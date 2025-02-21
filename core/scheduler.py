import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import register_events
from django.conf import settings
from .views import close, charge

# Initialize logger
logger = logging.getLogger(__name__)

# Create scheduler to run in a thread inside the application process
scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)

def start():
    try:
        if settings.DEBUG:
            # Enable detailed logging for debugging
            logging.basicConfig()
            logging.getLogger('apscheduler').setLevel(logging.DEBUG)

        # Schedule the 'close' job to run every hour
        scheduler.add_job(
            close,
            "cron",
            id="close_auction",
            hour='*',
            minute=0,  # Run at the start of every hour
            replace_existing=True,
        )

        # Schedule the 'charge' job to run every day at midnight
        scheduler.add_job(
            charge,
            "cron",
            id="storage_bill",
            hour=0,  # Midnight
            minute=0,
            replace_existing=True,
        )

        # Register scheduler events with Django admin
        register_events(scheduler)

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully.")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise