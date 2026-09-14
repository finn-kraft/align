"""Pure, deterministic cash-flow projection logic."""

from datetime import datetime
from typing import Any, Mapping


MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

MONTH_INPUT_FIELDS = (
    "income",
    "insurance",
    "utilities",
    "gas",
    "clothing",
    "fun",
    "eating_out",
    "giving",
    "car_repair",
    "other_amount",
)


def generate_month_sequence(start_month_name, count, start_year=None):
    """Return the existing simulator's month labels and stable input keys."""
    if count is None:
        count = 12
    if start_month_name is None:
        start_month_name = "Jan"
    if start_year is None:
        start_year = datetime.now().year

    start_index = MONTHS.index(start_month_name)
    months = []
    year = start_year
    month_index = start_index

    for _ in range(count):
        months.append(
            {
                "label": f"{MONTHS[month_index]} {year}",
                "key": f"{year}_{month_index + 1:02d}",
            }
        )
        month_index += 1
        if month_index > 11:
            month_index = 0
            year += 1

    return months


def compute_recurring_total(recurring):
    return sum(recurring.values())


def compute_variable_expenses(data):
    return (
        data["insurance"]
        + data["utilities"]
        + data["gas"]
        + data["clothing"]
        + data["fun"]
        + data["eating_out"]
        + data["giving"]
        + data["car_repair"]
        + data["other_amount"]
    )


def project_month(balance, income, recurring_total, variable_expenses, monthly_rate):
    interest_income = balance * monthly_rate
    net = income + interest_income - recurring_total - variable_expenses
    return {
        "interest_income": interest_income,
        "net": net,
        "new_balance": balance + net,
    }


def _normalise_month_inputs(data: Mapping[str, Any]) -> dict[str, Any]:
    """Match the Shiny adapter's historical missing-input behavior."""
    return {field: data.get(field, 0) or 0 for field in MONTH_INPUT_FIELDS}


def run_projection(
    state: Mapping[str, Any],
    monthly_inputs: Mapping[str, Mapping[str, Any]],
    *,
    start_year: int | None = None,
) -> list[dict[str, Any]]:
    """Project a scenario without UI, database, or framework dependencies."""
    months = state["months"]
    recurring_total = compute_recurring_total(state["recurring"])
    monthly_rate = state["apy"] / 100 / 12
    balance = state["starting_cash"]
    results = []

    for month in generate_month_sequence(state["start_month"], months, start_year):
        data = _normalise_month_inputs(monthly_inputs.get(month["key"], {}))
        variable = compute_variable_expenses(data)
        projection = project_month(
            balance,
            data["income"],
            recurring_total,
            variable,
            monthly_rate,
        )
        balance = projection["new_balance"]
        results.append(
            {
                "Month": month["label"],
                "Income": data["income"],
                "Interest Earned": round(projection["interest_income"], 2),
                "Recurring": recurring_total,
                "Variable": variable,
                "Net Change": round(projection["net"], 2),
                "Ending Balance": round(balance, 2),
            }
        )

    return results
