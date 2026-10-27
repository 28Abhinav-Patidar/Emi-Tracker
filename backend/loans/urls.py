
from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("loans/", views.LoanListCreateView.as_view(), name="loan-list"),
    path("loans/<int:pk>/", views.LoanDetailView.as_view(), name="loan-detail"),
    path(
        "loans/<int:pk>/status/",
        views.update_loan_status,
        name="loan-status",
    ),
    path(
        "loans/<int:pk>/schedule/",
        views.loan_schedule,
        name="loan-schedule",
    ),
]
