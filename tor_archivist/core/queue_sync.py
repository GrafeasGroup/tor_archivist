"""Functionality to sync the Blossom queue with the queue on Reddit."""
import logging
from typing import Any, Dict, Optional

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
    partner_submission = cfg.reddit.submission(url=r_submission.url)

    # Check if the post is marked as NSFW on the partner sub
    if not r_submission.over_18 and partner_submission.over_18:
        nsfw_on_reddit(r_submission)
        nsfw_on_blossom(cfg, b_submission)

    # Check if the post has been removed on the partner sub
    if partner_submission.removed_by_category:
        # Removed on the partner sub, it's safe to remove
        # But only do it if the submission is not marked as removed already
        if not r_submission.removed_by_category:
            remove_on_reddit(r_submission)
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
