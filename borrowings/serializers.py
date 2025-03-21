from rest_framework import serializers
from datetime import date

from .models import Borrowing
from books.serializers import BookSerializer
from user.serializers import UserSerializer


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        ]


class BorrowingCreateSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = ["id", "user", "book", "expected_return_date"]

    def validate_book(self, value):
        if value.inventory < 1:
            raise serializers.ValidationError("This book is out of stock.")
        return value

    def validate_expected_return_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Expected return date cannot be in the past.")
        return value

    def create(self, validated_data):
        book = validated_data["book"]
        if book.inventory < 1:
            raise serializers.ValidationError("This book is out of stock.")

        book.inventory -= 1
        book.save()

        return super().create(validated_data)


class BorrowingReturnSerializer(serializers.Serializer):
    def update(self, instance, validated_data):
        if instance.actual_return_date is not None:
            raise serializers.ValidationError("This book has already been returned.")
        instance.return_book()
        return instance
