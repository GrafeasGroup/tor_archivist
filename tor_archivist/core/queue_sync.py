"""Functionality to sync the Blossom queue with the queue on Reddit."""
import datetime
import logging
from typing import Any, Optional, Dict

from tor_archivist.core.config import Config


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

    return submissions[0]


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

        removal_response = cfg.blossom.patch(f"submission/{b_submission_id}/remove")
        if not removal_response.ok:
            logging.warning(
                f"Failed to remove submission {b_submission_id} ({tor_url}) from Blossom! "
                f"({removal_response.status_code})"
            )
            continue

        logging.info(f"Removed submission {b_submission_id} ({tor_url}) from Blossom.")


def track_post_reports(cfg: Config) -> None:
    """Process the mod queue and sync post reports to Blossom."""
    logging.info("Tracking post reports!")
    for r_submission in cfg.tor.mod.modqueue(only="submissions", limit=None):
        # Check if the report has already been handled
        if (
            r_submission.removed
            or r_submission.ignore_reports
            or r_submission.approved_at_utc
        ):
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
        b_submission_id = b_submission["id"]

        if b_submission["removed_from_queue"]:
            logging.debug(f"Submission {b_submission_id} has already been removed.")
            continue

        # TODO: Handle NSFW and removed posts automatically
        report_response = cfg.blossom.patch(
            f"submission/{b_submission_id}/report", data={"reason": reason}
        )
        if not report_response.ok:
            logging.warning(
                f"Failed to report submission {b_submission_id} ({tor_url}) to Blossom! "
                f"({report_response.status_code})"
            )
            continue

        # TODO: Don't log this if the post has already been reported on Blosssom
        # We might need to change the Blossom response in this case
        logging.info(f"Reported submission {b_submission_id} ({tor_url}) to Blossom.")
