from celery import shared_task
from django.utils import timezone
from .models import Borrowing
from .telegram_helper import send_telegram_message
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def check_overdue_borrowings():
    logger.info("Task 'check_overdue_borrowings' started.")
    today = timezone.now().date()
    logger.info(f"Today's date: {today}")

    overdue_borrowings = Borrowing.objects.filter(
        expected_return_date__lte=today,
        actual_return_date__isnull=True
    )

    logger.info(f"Found {overdue_borrowings.count()} overdue borrowings.")

    if overdue_borrowings.exists():
        for borrowing in overdue_borrowings:
            message = f"Overdue borrowing: {borrowing.book.title} borrowed by {borrowing.user.email} on {borrowing.borrow_date}"
            logger.info(f"Sending message: {message}")
            try:
                send_telegram_message(message)
                logger.info("Message sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
    else:
        logger.info("No borrowings overdue today.")
        try:
            send_telegram_message("No borrowings overdue today!")
            logger.info("Message sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
