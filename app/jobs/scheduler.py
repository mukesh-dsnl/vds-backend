import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from app.services.live_cache_service import refresh_live_cache
from app.services.simulation_service import generate_time_series

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the APScheduler background scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")

    schedule_live_cache_refresh()
    refresh_live_cache()


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down")


def schedule_simulation(campaign_id: str, run_at: datetime | None = None):
    """
    Schedule time-series generation for a campaign.

    Args:
        campaign_id: ID of the campaign to generate data for.
        run_at:      When to run. If None, runs immediately.
    """

    def _run():
        try:
            total = generate_time_series(campaign_id)
            logger.info(
                "Scheduled simulation for campaign %s completed — %d rows",
                campaign_id,
                total,
            )
        except Exception:
            logger.exception("Scheduled simulation failed for campaign %s", campaign_id)

    job_id = f"sim_campaign_{campaign_id}"

    if run_at:
        scheduler.add_job(_run, "date", run_date=run_at, id=job_id, replace_existing=True)
        logger.info("Scheduled simulation for campaign %s at %s", campaign_id, run_at)
    else:
        scheduler.add_job(_run, id=job_id, replace_existing=True)
        logger.info("Triggered immediate simulation for campaign %s", campaign_id)


def schedule_live_cache_refresh(interval_seconds: int = 5):
    """Schedule cache refresh to avoid per-request CSV reads."""

    def _run():
        try:
            refresh_live_cache()
            logger.debug("Live cache refreshed")
        except Exception:
            logger.exception("Live cache refresh failed")

    scheduler.add_job(
        _run,
        "interval",
        seconds=interval_seconds,
        id="live_cache_refresh",
        replace_existing=True,
    )
    logger.info("Live cache refresh scheduled every %ds", interval_seconds)
