
from decimal import Decimal

from rest_framework import serializers

from .models import Loan
from .calculations import calculate_emi, calculate_schedule, money


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = [
            "id",
            "emi",
            "total_interest",
            "total_payable",
            "status",
            "created_at",
        ]

    def validate_principal(self, value):
        if value < 10000 or value > 5000000:
            raise serializers.ValidationError(
                "Principal must be between 10000 and 5000000."
            )
        return value

    def validate_annual_interest_rate(self, value):
        if value < 1 or value > 36:
            raise serializers.ValidationError(
                "Annual interest rate must be between 1% and 36%."
            )
        return value

    def validate_tenure_months(self, value):
        if value < 3 or value > 60:
            raise serializers.ValidationError(
                "Tenure must be between 3 and 60 months."
            )
        return value

    def create(self, validated_data):
        principal = validated_data["principal"]
        rate = validated_data["annual_interest_rate"]
        months = validated_data["tenure_months"]

        emi = calculate_emi(principal, rate, months)
        schedule = calculate_schedule(principal, rate, months)

        total_payable = money(
            sum(
                (row["emi"] for row in schedule),
                Decimal("0.00"),
            )
        )
        total_interest = money(total_payable - principal)

        return Loan.objects.create(
            **validated_data,
            emi=emi,
            total_payable=total_payable,
            total_interest=total_interest,
        )
