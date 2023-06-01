import logging
from typing import Dict, Optional

from tor_archivist.core.config import Config


def get_blossom_submission(cfg: Config, tor_url: str) -> Optional[Dict]:
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


def report_handled_blossom(b_submission: Dict) -> bool:
    """Determine if the report is already handled on Blossom."""
    return (
        b_submission.get("removed_from_queue")
        # These are not exposed to the API yet
        # But it doesn't hurt to leave them in and it'll work if we ever expose them
        or b_submission.get("approved")
        or b_submission.get("report_reason")
    )


def remove_on_blossom(cfg: Config, b_submission: Dict) -> None:
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


def approve_on_blossom(cfg: Config, b_submission: Dict) -> None:
    """Approve the given submission on Blossom."""
    b_id = b_submission["id"]
    tor_url = b_submission["tor_url"]

    approve_response = cfg.blossom.patch(f"submission/{b_id}/approve")
    if approve_response.ok:
        logging.info(f"Approved submission {b_id} ({tor_url}) on Blossom.")
    else:
        logging.warning(
            f"Failed to approve submission {b_id} ({tor_url}) on Blossom! "
            f"({approve_response.status_code})"
        )


def nsfw_on_blossom(cfg: Config, b_submission: Dict) -> None:
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


def report_on_blossom(cfg: Config, b_submission: Dict, reason: str) -> None:
    """Report the submission on Blossom."""
    b_id = b_submission["id"]
    tor_url = b_submission["tor_url"]

    report_response = cfg.blossom.patch(f"submission/{b_id}/report", data={"reason": reason})
    if report_response.ok:
        logging.info(f"Reported submission {b_id} ({tor_url}) to Blossom.")
    else:
        logging.warning(
            f"Failed to report submission {b_id} ({tor_url}) to Blossom! "
            f"({report_response.status_code})"
        )
