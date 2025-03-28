from rest_framework import mixins, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Borrowing
from .serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)
from .telegram_helper import send_telegram_message


class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    pagination_class.page_size = 5

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter borrowings by user ID (for staff only).",
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter borrowings by active status (true/false).",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        book = serializer.validated_data["book"]
        if book.inventory < 1:
            return Response(
                {"detail": "This book is out of stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        borrowing = serializer.save(user=self.request.user)

        message = (
            f"New borrowing created!\n"
            f"Book title: {borrowing.book.title}\n"
            f"User: {borrowing.user.email}\n"
            f"Expected return date: {borrowing.expected_return_date}"
        )
        send_telegram_message(message)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        if user.is_staff:
            user_id = self.request.query_params.get("user_id")
            if user_id:
                queryset = queryset.filter(user_id=user_id)

        is_active = self.request.query_params.get("is_active")
        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset.distinct()

    @extend_schema(
        methods=["POST"],
        description="Return a borrowed book.",
        responses={200: {"description": "Book returned successfully."}},
    )
    @action(detail=True, methods=["post"], url_path="return")
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()
        serializer = BorrowingReturnSerializer(borrowing, data={})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "Book returned successfully."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
