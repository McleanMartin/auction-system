import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import register_events
from django.conf import settings
from django.utils import timezone
from .models import *
from django.core.mail import send_mail
from django.conf import settings

# # Initialize logger
logger = logging.getLogger(__name__)

# Create scheduler to run in a thread inside the application process
scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)

def close():
    """
    Close expired auctions and notify the winning bidder.
    """
    try:
        # Get all active auctions that have ended
        auctions = Auction.objects.filter(expired=False, end_date__lte=timezone.now())

        for auction in auctions:
            # Mark the auction as expired
            auction.expired = True
            auction.save()

            # Find the last bidder for the auction
            last_bidder = AuctionBid.objects.filter(auction=auction).last()
    
            if last_bidder:
                # Mark the last bidder as the winner
                last_bidder.winner = True
                last_bidder.product.sold = True
                last_bidder.product.save()
                last_bidder.save()


        logger.info("Successfully closed expired auctions.")
    except Exception as e:
        # logger.error(f"Error in close function: {e}")
        raise

def start():
    """
    Start the scheduler and register the 'close' job.
    """
    try:
        # if settings.DEBUG:
        #     # Enable detailed logging for debugging
        #     logging.basicConfig()
        #     logging.getLogger('apscheduler').setLevel(logging.DEBUG)

        # Schedule the 'close' job to run every hour
        scheduler.add_job(
            close,
            "interval",
            seconds=3,  
            id="close_auction",
            replace_existing=True,
        )

        register_events(scheduler)
        scheduler.start()
        # logger.info("Scheduler started successfully.")

    except Exception as e:
        # logger.error(f"Failed to start scheduler: {e}")
        raise