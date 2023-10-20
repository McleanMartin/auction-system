import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from django_apscheduler.jobstores import register_events, register_job
from .views import pre_bidder

from django.conf import settings


# Create scheduler to run in a thread inside the application process
scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)

def start():
    if settings.DEBUG:
      	# Hook into the apscheduler logger
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)
        
    scheduler.add_job(pre_bidder, "cron", id="pre_bidder", hour= '10', second='*/10',replace_existing=True )
    
    # Add the scheduled jobs to the admin interface
    register_events(scheduler)

    scheduler.start()