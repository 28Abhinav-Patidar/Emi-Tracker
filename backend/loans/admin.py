from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant_name",
        "applicant_email",
        "principal",
        "annual_interest_rate",
        "tenure_months",
        "emi",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("applicant_name", "applicant_email")
    ordering = ("-created_at",)
    # Calculated by the backend, so they can't be edited by hand.
    readonly_fields = ("emi", "total_interest", "total_payable", "created_at")
