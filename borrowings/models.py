from django.utils import timezone
from django.db import models
from books.models import Book
from django.contrib.auth import get_user_model

User = get_user_model()


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrowings")

    def __str__(self):
        return f"{self.user.email} borrowed {self.book.title} on {self.borrow_date}"

    class Meta:
        ordering = ["-borrow_date"]

    def return_book(self):
        if self.actual_return_date is not None:
            raise ValueError("This book has already been returned.")
        self.actual_return_date = timezone.now().date()
        self.book.inventory += 1
        self.book.save()
        self.save()
