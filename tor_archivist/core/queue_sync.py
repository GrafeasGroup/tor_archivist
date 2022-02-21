"""Functionality to sync the Blossom queue with the queue on Reddit."""
import datetime
import logging
from typing import Any, Optional, Dict

from tor_archivist.core.config import Config


NSFW_POST_REPORT_REASON = "Post should be marked as NSFW"


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


def _get_blossom_submission(cfg: Config, tor_url: str) -> Optional[Dict]:
    """Get the Blossom submission corresponding to the given ToR URL.

    :returns: The Blossom submission object or None if it couldn't be found.
    """
    submission_response = cfg.blossom.get("submission", params={"tor_url": tor_url})
    if not submission_response.ok:
        return None

    submissions = submission_response.json()["results"]
    if len(submissions) == 0:
        return None

    submission = submissions[0]
    return submission


def _report_handled_reddit(r_submission: Any) -> bool:
    """Determine if the report is already handled on Reddit."""
    return (
        r_submission.removed
        or r_submission.ignore_reports
        or r_submission.approved_at_utc
    )


def _report_handled_blossom(b_submission: Dict) -> bool:
    """Determine if the report is already handled on Blossom."""
    return (
        b_submission.get("removed_from_queue")
        # These are not exposed to the API yet
        # But it doesn't hurt to leave them in and it'll work if we ever expose them
        or b_submission.get("approved")
        or b_submission.get("report_reason")
    )


def _remove_on_reddit(r_submission: Any) -> None:
    """Remove the given submission from Reddit."""
    r_submission.mod.remove()


def _remove_on_blossom(cfg: Config, b_submission: Dict) -> None:
    """Remove the given submission from Blossom."""
    b_id = b_submission["id"]
    tor_url = b_submission["tor_url"]

    removal_response = cfg.blossom.patch(f"submission/{b_id}/remove")
    if removal_response.ok:
        logging.info(f"Removed submission {b_id} ({tor_url}) from Blossom.")
    else:
        logging.warning(
            f"Failed to remove submission {b_id} ({tor_url}) from Blossom! "
            f"({removal_response.status_code})"
        )


def _nsfw_on_reddit(r_submission: Any) -> None:
    """Mark the submission as NSFW on Reddit."""
    r_submission.mod.nsfw()


def _nsfw_on_blossom(cfg: Config, b_submission: Dict) -> None:
    """Mark the submission as NSFW on Blossom."""
    b_id = b_submission["id"]
    tor_url = b_submission["tor_url"]

    nsfw_response = cfg.blossom.patch(f"submission/{b_id}/nsfw")
    if nsfw_response.ok:
        logging.info(f"Submission {b_id} ({tor_url}) marked as NSFW on Blossom.")
    else:
        logging.warning(
            f"Failed to mark submission {b_id} ({tor_url}) as NSFW on Blossom! "
            f"({nsfw_response.status_code})"
        )


def _report_on_blossom(cfg: Config, b_submission: Dict, reason: str) -> None:
    """Report the submission on Blossom."""
    b_id = b_submission["id"]
    tor_url = b_submission["tor_url"]

    report_response = cfg.blossom.patch(
        f"submission/{b_id}/report", data={"reason": reason}
    )
    if report_response.ok:
        logging.info(f"Reported submission {b_id} ({tor_url}) to Blossom.")
    else:
        logging.warning(
            f"Failed to report submission {b_id} ({tor_url}) to Blossom! "
            f"({report_response.status_code})"
        )


def _auto_report_handling(
    cfg: Config, r_submission: Any, b_submission: Dict, reason: str
) -> bool:
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
    if partner_submission.over_18:
        _nsfw_on_reddit(r_submission)
        _nsfw_on_blossom(cfg, b_submission)

    # Check if the post has been removed on the partner sub
    if partner_submission.removed_by_category:
        # Removed on the partner sub, it's safe to remove
        _remove_on_reddit(r_submission)
        _remove_on_blossom(cfg, b_submission)
        # We can ignore the report
        return True

    if reason == NSFW_POST_REPORT_REASON:
        # We already handled NSFW reports
        return True

    return False


def track_post_removal(cfg: Config) -> None:
    """Process the mod log and sync post removals to Blossom."""
    for log in cfg.tor.mod.log(action="removelink", limit=100):
        mod = log.mod
        tor_url = "https://reddit.com" + log.target_permalink
        create_time = datetime.datetime.fromtimestamp(log.created_utc)

        if mod.name.casefold() in ["tor_archivist", "blossom"]:
            # Ignore our bots to avoid doing the same thing twice
            continue

        if create_time <= cfg.last_post_scan_time:
            continue

        # Fetch the corresponding submission from Blossom
        b_submission = _get_blossom_submission(cfg, tor_url)
        if b_submission is None:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        b_submission_id = b_submission["id"]

        if b_submission["removed_from_queue"]:
            logging.debug(f"Submission {b_submission_id} has already been removed.")
            continue

        _remove_on_blossom(cfg, b_submission)


def track_post_reports(cfg: Config) -> None:
    """Process the mod queue and sync post reports to Blossom."""
    logging.info("Tracking post reports!")
    for r_submission in cfg.tor.mod.modqueue(only="submissions", limit=None):
        # Check if the report has already been handled
        if _report_handled_reddit(r_submission):
            continue

        # Determine the report reason
        reason = _get_report_reason(r_submission)
        if reason is None:
            continue

        tor_url = "https://reddit.com" + r_submission.permalink

        # Fetch the corresponding submission from Blossom
        b_submission = _get_blossom_submission(cfg, tor_url)
        if b_submission is None:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        b_id = b_submission["id"]

        if _report_handled_blossom(b_submission):
            logging.debug(f"Submission {b_id} has already been removed.")
            continue

        # Handle the report automatically if possible
        # In that case we don't need to send it to Blossom
        if _auto_report_handling(cfg, r_submission, b_submission, reason):
            continue

        _report_on_blossom(cfg, b_submission, reason)
