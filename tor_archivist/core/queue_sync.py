"""Functionality to sync the Blossom queue with the queue on Reddit."""
import datetime
import logging

from tor_archivist.core.config import Config


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
        submission_response = cfg.blossom.get("submission", params={"tor_url": tor_url})
        if not submission_response.ok:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submissions = submission_response.json()["results"]
        if len(submissions) == 0:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submission = submissions[0]
        submission_id = submission["id"]

        if submission["removed_from_queue"]:
            logging.debug(f"Submission {submission_id} has already been removed.")
            continue

        removal_response = cfg.blossom.patch(f"submission/{submission_id}/remove")
        if not removal_response.ok:
            logging.warning(
                f"Failed to remove submission {submission_id} ({tor_url}) from Blossom! "
                f"({removal_response.status_code})"
            )
            continue

        logging.info(f"Removed submission {submission_id} ({tor_url}) from Blossom.")


def track_post_reports(cfg: Config) -> None:
    """Process the mod queue and sync post reports to Blossom."""
    logging.info("Tracking post reports!")
    for submission in cfg.tor.mod.modqueue(only="submissions", limit=None):
        # Check if the report has already been handled
        if (
            submission.removed
            or submission.ignore_reports
            or submission.approved_at_utc
        ):
            continue

        # Determine the report reason
        reason = (
            submission.mod_reports[0][0]
            if len(submission.mod_reports) > 0
            else submission.user_reports[0][0]
            if len(submission.user_reports) > 0
            else None
        )
        if reason is None:
            continue

        tor_url = "https://reddit.com" + submission.permalink

        # Fetch the corresponding submission from Blossom
        submission_response = cfg.blossom.get("submission", params={"tor_url": tor_url})
        if not submission_response.ok:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submissions = submission_response.json()["results"]
        if len(submissions) == 0:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submission = submissions[0]
        submission_id = submission["id"]

        if submission["removed_from_queue"]:
            logging.debug(f"Submission {submission_id} has already been removed.")
            continue

        # TODO: Handle NSFW and removed posts automatically
        report_response = cfg.blossom.patch(
            f"submission/{submission_id}/report", data={"reason": reason}
        )
        if not report_response.ok:
            logging.warning(
                f"Failed to report submission {submission_id} ({tor_url}) to Blossom! "
                f"({report_response.status_code})"
            )
            continue

        # TODO: Don't log this if the post has already been reported on Blosssom
        # We might need to change the Blossom response in this case
        logging.info(f"Reported submission {submission_id} ({tor_url}) to Blossom.")
