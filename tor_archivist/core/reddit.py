import logging
from typing import Any


def report_handled_reddit(r_submission: Any) -> bool:
    """Determine if the report is already handled on Reddit."""
    return r_submission.removed or r_submission.ignore_reports or r_submission.approved_at_utc


def remove_on_reddit(r_submission: Any) -> None:
    """Remove the given submission from Reddit."""
    r_submission.mod.remove()
    logging.info(f"Removed submission {r_submission.url} from Reddit.")


def approve_on_reddit(r_submission: Any) -> None:
    """Approve the given submission on Reddit."""
    r_submission.mod.approve()
    r_submission.mod.ignore_reports()
    logging.info(f"Approved submission {r_submission.url} on Reddit.")


def nsfw_on_reddit(r_submission: Any) -> None:
    """Mark the submission as NSFW on Reddit."""
    r_submission.mod.nsfw()
    logging.info(f"Submission {r_submission.url} marked as NSFW on Reddit.")
