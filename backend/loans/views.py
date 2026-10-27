
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Loan
from .serializers import LoanSerializer
from .calculations import calculate_schedule


@api_view(["GET"])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


class LoanListCreateView(generics.ListCreateAPIView):
    serializer_class = LoanSerializer
    queryset = Loan.objects.all().order_by("-created_at")


class LoanDetailView(generics.RetrieveAPIView):
    serializer_class = LoanSerializer
    queryset = Loan.objects.all()


@api_view(["PATCH"])
def update_loan_status(request, pk):
    loan = get_object_or_404(Loan, pk=pk)

    if loan.status != Loan.Status.PENDING:
        return Response(
            {"error": "Only pending loans can change status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    new_status = request.data.get("status")

    if new_status not in [Loan.Status.APPROVED, Loan.Status.REJECTED]:
        return Response(
            {"error": "Status must be APPROVED or REJECTED."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    loan.status = new_status
    loan.save(update_fields=["status"])

    return Response(LoanSerializer(loan).data)


@api_view(["GET"])
def loan_schedule(request, pk):
    loan = get_object_or_404(Loan, pk=pk)

    rows = calculate_schedule(
        loan.principal,
        loan.annual_interest_rate,
        loan.tenure_months,
    )

    return Response([
        {
            key: str(value) if key != "month" else value
            for key, value in row.items()
        }
        for row in rows
    ])
