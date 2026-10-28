from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .calculations import calculate_emi, calculate_schedule
from .models import Loan


class EmiCalculationTests(SimpleTestCase):
    def test_sanity_check_from_assignment(self):
        # ₹1,00,000 at 12% for 12 months -> ₹8,884.88
        self.assertEqual(calculate_emi(100000, 12, 12), Decimal("8884.88"))

    def test_emi_is_rounded_to_two_decimals(self):
        emi = calculate_emi(Decimal("12345.67"), Decimal("7.25"), 37)
        self.assertEqual(emi.as_tuple().exponent, -2)

    def test_emi_returns_decimal(self):
        self.assertIsInstance(calculate_emi(50000, 10, 24), Decimal)

    def test_range_boundaries(self):
        self.assertEqual(calculate_emi(10000, 1, 3), Decimal("3338.89"))
        self.assertEqual(calculate_emi(5000000, 36, 60), Decimal("180664.79"))


class ScheduleCalculationTests(SimpleTestCase):
    CASES = [
        (Decimal("100000"), Decimal("12"), 12),
        (Decimal("10000"), Decimal("1"), 3),
        (Decimal("5000000"), Decimal("36"), 60),
        (Decimal("12345.67"), Decimal("7.25"), 37),
    ]

    def test_schedule_has_one_row_per_month(self):
        for principal, rate, months in self.CASES:
            with self.subTest(principal=principal, rate=rate, months=months):
                rows = calculate_schedule(principal, rate, months)
                self.assertEqual([r["month"] for r in rows], list(range(1, months + 1)))

    def test_final_balance_is_exactly_zero(self):
        for principal, rate, months in self.CASES:
            with self.subTest(principal=principal, rate=rate, months=months):
                rows = calculate_schedule(principal, rate, months)
                self.assertEqual(rows[-1]["remaining_balance"], Decimal("0.00"))

    def test_principal_components_add_up_to_principal(self):
        for principal, rate, months in self.CASES:
            with self.subTest(principal=principal, rate=rate, months=months):
                rows = calculate_schedule(principal, rate, months)
                total = sum((r["principal_component"] for r in rows), Decimal("0"))
                self.assertEqual(total, principal)

    def test_each_row_balances(self):
        # emi = principal + interest, and balance drops by the principal paid.
        principal, rate, months = self.CASES[0]
        rows = calculate_schedule(principal, rate, months)
        balance = principal
        for row in rows:
            self.assertEqual(row["emi"], row["principal_component"] + row["interest_component"])
            balance -= row["principal_component"]
            self.assertEqual(row["remaining_balance"], balance)

    def test_all_rows_except_last_use_regular_emi(self):
        rows = calculate_schedule(Decimal("100000"), Decimal("12"), 12)
        for row in rows[:-1]:
            self.assertEqual(row["emi"], Decimal("8884.88"))

    def test_first_month_interest(self):
        rows = calculate_schedule(Decimal("100000"), Decimal("12"), 12)
        # 1,00,000 x 1% = 1,000.00
        self.assertEqual(rows[0]["interest_component"], Decimal("1000.00"))
        self.assertEqual(rows[0]["principal_component"], Decimal("7884.88"))


class LoanApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "applicant_name": "Rahul Sharma",
            "applicant_email": "rahul@example.com",
            "principal": "100000.00",
            "annual_interest_rate": "12.00",
            "tenure_months": 12,
        }

    def test_create_calculates_emi_and_ignores_client_values(self):
        response = self.client.post(
            "/api/loans/",
            {**self.payload, "emi": "1.00", "status": "APPROVED"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["emi"], "8884.88")
        self.assertEqual(response.data["total_payable"], "106618.53")
        self.assertEqual(response.data["total_interest"], "6618.53")
        self.assertEqual(response.data["status"], "PENDING")

    def test_invalid_input_returns_400(self):
        bad_values = {
            "principal": "9999.99",
            "annual_interest_rate": "36.01",
            "tenure_months": 61,
            "applicant_email": "not-an-email",
        }
        for field, value in bad_values.items():
            with self.subTest(field=field):
                response = self.client.post(
                    "/api/loans/", {**self.payload, field: value}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_status_can_change_only_while_pending(self):
        loan_id = self.client.post("/api/loans/", self.payload, format="json").data["id"]
        url = f"/api/loans/{loan_id}/status/"

        response = self.client.patch(url, {"status": "APPROVED"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Loan.objects.get(pk=loan_id).status, "APPROVED")

        response = self.client.patch(url, {"status": "REJECTED"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Loan.objects.get(pk=loan_id).status, "APPROVED")

    def test_invalid_status_value_returns_400(self):
        loan_id = self.client.post("/api/loans/", self.payload, format="json").data["id"]
        response = self.client.patch(
            f"/api/loans/{loan_id}/status/", {"status": "PENDING"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_schedule_endpoint(self):
        loan_id = self.client.post("/api/loans/", self.payload, format="json").data["id"]
        response = self.client.get(f"/api/loans/{loan_id}/schedule/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 12)
        self.assertEqual(
            set(response.data[0]),
            {"month", "emi", "principal_component", "interest_component", "remaining_balance"},
        )
        self.assertEqual(response.data[-1]["remaining_balance"], "0.00")
