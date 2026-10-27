
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_emi(principal, annual_interest_rate, tenure_months):
    principal = Decimal(str(principal))
    annual_interest_rate = Decimal(str(annual_interest_rate))

    monthly_rate = annual_interest_rate / Decimal("1200")
    months = int(tenure_months)

    if monthly_rate == 0:
        return money(principal / months)

    factor = (Decimal("1") + monthly_rate) ** months

    emi = principal * monthly_rate * factor / (factor - Decimal("1"))

    return money(emi)



def calculate_schedule(principal, annual_interest_rate, tenure_months):
    principal = Decimal(str(principal))
    annual_interest_rate = Decimal(str(annual_interest_rate))
    months = int(tenure_months)

    emi = calculate_emi(principal, annual_interest_rate, months)
    monthly_rate = annual_interest_rate / Decimal("1200")

    balance = principal
    schedule = []

    for month in range(1, months + 1):
        interest = money(balance * monthly_rate)

        if month == months:
            # Adjust the final row to clear rounding differences.
            principal_component = balance
            actual_emi = money(principal_component + interest)
            balance = Decimal("0.00")
        else:
            principal_component = money(emi - interest)
            actual_emi = emi
            balance = money(balance - principal_component)

        schedule.append({
            "month": month,
            "emi": actual_emi,
            "principal_component": principal_component,
            "interest_component": interest,
            "remaining_balance": balance,
        })

    return schedule
