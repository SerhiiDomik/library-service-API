from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=255, unique=True)
    author = models.CharField(max_length=255)
    inventory = models.IntegerField()  # більше 0
    daily_fee = models.DecimalField(decimal_places=2, max_digits=4)

    def __str__(self):
        return self.title
