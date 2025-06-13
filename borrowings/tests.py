from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from datetime import date, timedelta
import uuid

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer

BORROWING_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def sample_book(**params):
    defaults = {
        "title": f"Sample Book {uuid.uuid4().hex[:6]}",
        "author": "Sample Author",
        "cover": Book.CoverChoices.SOFT,
        "inventory": 10,
        "daily_fee": 5.99,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def sample_borrowing(**params):
    defaults = {
        "expected_return_date": date.today() + timedelta(days=7),
        "book": sample_book(),
        "user": get_user_model().objects.create_user(
            email=f"test {uuid.uuid4().hex[:3]} @test.com", password="testpass"
        ),
    }
    defaults.update(params)
    return Borrowing.objects.create(**defaults)


class UnauthenticatedBorrowingApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_borrowings(self):
        sample_borrowing(user=self.user)
        sample_borrowing(user=self.user)

        response = self.client.get(BORROWING_URL)
        borrowings = Borrowing.objects.filter(user=self.user)
        serializer = BorrowingSerializer(borrowings, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_cannot_see_others_borrowings(self):
        other_user = get_user_model().objects.create_user(
            email="other@test.com", password="otherpass"
        )
        other_borrowing = sample_borrowing(user=other_user)

        my_borrowing = sample_borrowing(user=self.user)

        response = self.client.get(BORROWING_URL)
        borrowings = response.data["results"]

        borrowing_ids = [b["id"] for b in borrowings]
        self.assertIn(my_borrowing.id, borrowing_ids)
        self.assertNotIn(other_borrowing.id, borrowing_ids)

        url = detail_url(other_borrowing.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_borrowing_detail(self):
        borrowing = sample_borrowing(user=self.user)
        url = detail_url(borrowing.id)

        response = self.client.get(url)
        serializer = BorrowingSerializer(borrowing)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_borrowing(self):
        book = sample_book(inventory=5)
        payload = {
            "book": book.id,
            "expected_return_date": date.today() + timedelta(days=14),
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        borrowing = Borrowing.objects.get(id=response.data["id"])
        book.refresh_from_db()
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(book.inventory, 4)

    def test_create_borrowing_out_of_stock(self):
        book = sample_book(inventory=0)
        payload = {
            "book": book.id,
            "expected_return_date": date.today() + timedelta(days=14),
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_borrowing_invalid_return_date(self):
        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": date.today() - timedelta(days=1),
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_borrowings_by_is_active(self):
        borrowing1 = sample_borrowing(user=self.user)
        borrowing2 = sample_borrowing(user=self.user, actual_return_date=date.today())
        response = self.client.get(BORROWING_URL, {"is_active": "true"})
        serializer1 = BorrowingSerializer(borrowing1)
        serializer2 = BorrowingSerializer(borrowing2)

        self.assertIn(serializer1.data, response.data["results"])
        self.assertNotIn(serializer2.data, response.data["results"])

    def test_borrowing_return(self):
        borrowing = sample_borrowing(user=self.user)
        url = detail_url(borrowing.id) + "return/"

        response = self.client.post(url)
        borrowing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(borrowing.actual_return_date)
        self.assertEqual(borrowing.book.inventory, 11)

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        borrowing.book.refresh_from_db()
        self.assertEqual(borrowing.book.inventory, 11)


class AdminBorrowingApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="testpass"
        )

    def test_filter_borrowings_by_user(self):
        borrowing1 = sample_borrowing(user=self.user)
        borrowing2 = sample_borrowing(user=self.admin_user)

        response = self.client.get(BORROWING_URL, {"user_id": self.user.id})
        serializer1 = BorrowingSerializer(borrowing1)
        serializer2 = BorrowingSerializer(borrowing2)

        self.assertIn(serializer1.data, response.data["results"])
        self.assertNotIn(serializer2.data, response.data["results"])

    def test_list_all_borrowings(self):
        sample_borrowing(user=self.user)
        sample_borrowing(user=self.admin_user)

        response = self.client.get(BORROWING_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)


class TelegramNotificationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="testpass"
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book(inventory=5)

    @patch("borrowings.views.send_telegram_message")
    def test_send_telegram_message_on_borrowing_creation(self, mock_send):
        """Test that Telegram message is sent when creating a borrowing"""
        payload = {
            "book": self.book.id,
            "expected_return_date": date.today() + timedelta(days=14),
        }

        response = self.client.post(BORROWING_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_send.called)
