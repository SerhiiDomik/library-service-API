from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from books.serializers import BookSerializer

BOOK_URL = reverse("books:book-list")


def detail_url(book_id):
    return reverse("books:book-detail", args=[book_id])


def sample_book(**params):
    defaults = {
        "title": "Sample Book",
        "author": "Sample Author",
        "cover": Book.CoverChoices.SOFT,
        "inventory": 10,
        "daily_fee": 5.99,
    }
    defaults.update(params)

    return Book.objects.create(**defaults)


class UnauthenticatedBookApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(BOOK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticatedBookApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_list_books(self):
        sample_book(title="Book 1")
        sample_book(title="Book 2")

        response = self.client.get(BOOK_URL)
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_retrieve_book_detail(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.get(url)
        serializer = BookSerializer(book)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_books_by_title(self):
        book1 = sample_book(title="Django for Beginners")
        book2 = sample_book(title="Python Tricks")
        book3 = sample_book(title="Another Django Book")

        response = self.client.get(BOOK_URL, {"title": "django"})

        serializer1 = BookSerializer(book1)
        serializer2 = BookSerializer(book2)
        serializer3 = BookSerializer(book3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, response.data["results"])
        self.assertNotIn(serializer2.data, response.data["results"])
        self.assertIn(serializer3.data, response.data["results"])

    def test_filter_books_by_author(self):
        book1 = sample_book(title="Django for Beginners", author="J.K. Rowling")
        book2 = sample_book(title="Python Tricks", author="Stephen King")
        book3 = sample_book(title="Another Django Book", author="George R.R. Martin")

        response = self.client.get(BOOK_URL, {"author": "king"})

        serializer1 = BookSerializer(book1)
        serializer2 = BookSerializer(book2)
        serializer3 = BookSerializer(book3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer1.data, response.data["results"])
        self.assertIn(serializer2.data, response.data["results"])
        self.assertNotIn(serializer3.data, response.data["results"])

    def test_create_book_forbidden(self):
        payload = {
            "title": "New Book",
            "author": "New Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 15,
            "daily_fee": 9.99,
        }

        response = self.client.post(BOOK_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_book_forbidden(self):
        book = sample_book()
        payload = {"title": "Updated Title"}

        url = detail_url(book.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_book_forbidden(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_book(self):
        payload = {
            "title": "Admin's Book",
            "author": "Admin Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 20,
            "daily_fee": 12.99,
        }

        response = self.client.post(BOOK_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_book(self):
        book = sample_book()
        payload = {
            "title": "Updated Title",
            "daily_fee": 7.99,
        }

        url = detail_url(book.id)
        response = self.client.patch(url, payload)

        book.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(book.title, payload["title"])
        self.assertEqual(float(book.daily_fee), payload["daily_fee"])

    def test_delete_book(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_unique_title_constraint(self):
        sample_book(title="Unique Book")
        payload = {
            "title": "Unique Book",
            "author": "Some Author",
            "cover": Book.CoverChoices.SOFT,
            "inventory": 5,
            "daily_fee": 4.99,
        }

        response = self.client.post(BOOK_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
