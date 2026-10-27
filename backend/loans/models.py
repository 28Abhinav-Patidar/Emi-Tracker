from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    applicant_name = models.CharField(max_length=150)

    applicant_email = models.EmailField()

    principal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(10000),
            MaxValueValidator(5000000),
        ],
    )

    annual_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(36),
        ],
    )

    tenure_months = models.PositiveIntegerField(
        validators=[
            MinValueValidator(3),
            MaxValueValidator(60),
        ]
    )

    emi = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    total_interest = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    total_payable = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.applicant_name} - {self.status}"
