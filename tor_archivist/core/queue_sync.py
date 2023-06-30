"""Functionality to sync the Blossom queue with the queue on Reddit."""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from prawcore import Forbidden

from tor_archivist.core.blossom import (
    approve_on_blossom,
    get_blossom_submission,
    nsfw_on_blossom,
    remove_on_blossom,
    report_handled_blossom,
    report_on_blossom,
)
from tor_archivist.core.config import Config
from tor_archivist.core.reddit import (
    approve_on_reddit,
    nsfw_on_reddit,
    remove_on_reddit,
    report_handled_reddit,
)

NSFW_POST_REPORT_REASON = "Post should be marked as NSFW"
BOT_USERNAMES = ["tor_archivist", "blossom", "tor_tester"]
QUEUE_TIMEOUT = timedelta(hours=18)


def _get_report_reason(r_submission: Any) -> Optional[str]:
    """Get the report reason for a Reddit submission."""
    return (
        # Prefer a report by a mod
        r_submission.mod_reports[0][0]
        if len(r_submission.mod_reports) > 0
        # Otherwise look for a user report
        else r_submission.user_reports[0][0]
        if len(r_submission.user_reports) > 0
        # No report available
        else None
    )


def _auto_report_handling(cfg: Config, r_submission: Any, b_submission: Dict, reason: str) -> bool:
    """Check if the report can be handled automatically.

    This is possible in the following cases:
    - The post has been removed on the partner sub. We can just delete remove
      it from the queue too.
    - The post has been reported as NSFW. We can check if the post has
      been marked as NSFW on the partner sub. If yes, we mark it as
      NSFW on both Reddit and Blossom. Otherwise, we ignore the report.

    :returns: True if the report has been handled automatically, else False.
    """
    try:
        partner_submission = cfg.reddit.submission(url=r_submission.url)

        # Check if the post is marked as NSFW on the partner sub
        if partner_submission.over_18:
            if not r_submission.over_18:
                nsfw_on_reddit(r_submission)
            if not b_submission["nsfw"]:
                nsfw_on_blossom(cfg, b_submission)

        # Check if the post has been removed on the partner sub
        if partner_submission.removed_by_category:
            # Removed on the partner sub, it's safe to remove
            # But only do it if the submission is not marked as removed already
            if not r_submission.removed_by_category:
                remove_on_reddit(r_submission)
            if not b_submission["removed_from_queue"]:
                remove_on_blossom(cfg, b_submission)
            # We can ignore the report
            return True

        # Check if the post has been removed by a mod
        if r_submission.removed_by_category:
            if not b_submission["removed_from_queue"]:
                remove_on_blossom(cfg, b_submission)
            # We can ignore the report
            return True

        if reason == NSFW_POST_REPORT_REASON:
            # We already handled NSFW reports
            # We still need to approve the submission to remove the item from mod queue
            approve_on_reddit(r_submission)
            approve_on_blossom(cfg, b_submission)
            return True

        return False
    except Forbidden:
        # The subreddit is private, remove the post from the queue
        logging.warning(f"Removing submission from private sub: {b_submission['tor_url']}")
        if not r_submission.removed_by_category:
            remove_on_reddit(r_submission)
        if not b_submission["removed_from_queue"]:
            remove_on_blossom(cfg, b_submission)
        return True


def track_post_removal(cfg: Config) -> None:
    """Process the mod log and sync post removals to Blossom."""
    logging.info("Tracking post removals!")
    for log in cfg.tor.mod.log(action="removelink", limit=100):
        mod = log.mod
        tor_url = "https://reddit.com" + log.target_permalink

        if mod.name.casefold() in BOT_USERNAMES:
            # Ignore our bots to avoid doing the same thing twice
            continue

        # Fetch the corresponding submission from Blossom
        b_submission = get_blossom_submission(cfg, tor_url)
        if b_submission is None:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        b_submission_id = b_submission["id"]

        if b_submission["removed_from_queue"]:
            logging.debug(f"Submission {b_submission_id} has already been removed.")
            continue

        remove_on_blossom(cfg, b_submission)


def track_post_reports(cfg: Config) -> None:
    """Process the mod queue and sync post reports to Blossom."""
    logging.info("Tracking post reports!")
    for r_submission in cfg.tor.mod.modqueue(only="submissions", limit=None):
        # Check if the report has already been handled
        if report_handled_reddit(r_submission):
            continue

        # Determine the report reason
        reason = _get_report_reason(r_submission)
        if reason is None:
            continue

        tor_url = "https://reddit.com" + r_submission.permalink

        # Fetch the corresponding submission from Blossom
        b_submission = get_blossom_submission(cfg, tor_url)
        if b_submission is None:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        b_id = b_submission["id"]

        if report_handled_blossom(b_submission):
            logging.debug(f"Submission {b_id} has already been removed.")
            continue

        # Handle the report automatically if possible
        # In that case we don't need to send it to Blossom
        if _auto_report_handling(cfg, r_submission, b_submission, reason):
            continue

        report_on_blossom(cfg, b_submission, reason)


def full_blossom_queue_sync(cfg: Config) -> None:
    """Make sure all posts in Blossom's queue still exist in Reddit."""
    queue_start = datetime.now(tz=timezone.utc) - QUEUE_TIMEOUT

    size = 500
    page = 1

    # Fetch all unclaimed posts from the queue
    while True:
        queue_response = cfg.blossom.get(
            "submission/",
            params={
                "page_size": size,
                "page": page,
                "claimed_by__isnull": True,
                "removed_from_queue": False,
                "create_time__gte": queue_start.isoformat(),
            },
        )
        if not queue_response.ok:
            logging.error(f"Failed to get queue from Blossom:\n{queue_response}")
            return

        data = queue_response.json()["results"]
        page += 1

        # Sync up the queue submissions
        for b_submission in data:
            logging.info(f"Syncing up Blossom queue for {b_submission['tor_url']}")
            r_submission = cfg.reddit.submission(url=b_submission["tor_url"])
            _auto_report_handling(cfg, r_submission, b_submission, "")
            time.sleep(1)

        if len(data) < size or queue_response.json()["next"] is None:
            break
