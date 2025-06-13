from datetime import date

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
        expected_return_date__lte=today, actual_return_date__isnull=True
    )

    logger.info(f"Found {overdue_borrowings.count()} overdue borrowings.")

    if overdue_borrowings.exists():
        for borrowing in overdue_borrowings:
            days_overdue = (date.today() - borrowing.expected_return_date).days

            message = (
                f"Overdue borrowing: borrowing id - {borrowing.id}.\n"
                f"Borrowed by {borrowing.user.email}.\n"
                f"Borrowed date {borrowing.borrow_date}.\n"
                f"Expected return date: {borrowing.expected_return_date}.\n"
                f"Overdue: {days_overdue} days."
            )
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
