import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import register_events
from django.conf import settings
from .views import close

# Initialize logger
logger = logging.getLogger(__name__)

# Create scheduler to run in a thread inside the application process
scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)

def start():
    try:
        if settings.DEBUG:
          pass
            # Enable detailed logging for debugging
            # logging.basicConfig()
            # logging.getLogger('apscheduler').setLevel(logging.DEBUG)

        # Schedule the 'close' job to run every hour
        scheduler.add_job(
            close,
            "cron",
            id="close_auction",
            hour='*',
            minute=0,  # Run at the start of every hour
            replace_existing=True,
        )

        register_events(scheduler)
        scheduler.start()
        logger.info("Scheduler started successfully.")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise