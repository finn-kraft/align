"""Shiny dialog for running electricity forecasts into cash flow."""

from __future__ import annotations

import pandas as pd
from shiny import reactive, render, ui

from cashflow.electricity_integration import (
    build_average_weather,
    build_occupancy_schedule,
    forecast_to_cashflow_months,
    uploaded_file_path,
    validate_occupancy_dates,
)


def electricity_forecast_dialog_ui():
    return ui.div(
        ui.h4("Electricity forecast"),
        ui.p(
            "Upload historical usage, then add one or more occupancy periods. "
            "Weather uses the average highs and lows from the temperature history."
        ),
        ui.input_file("electricity_usage_upload", "Upload usage.csv", accept=[".csv"]),
        ui.output_ui("electricity_occupancy_periods"),
        ui.input_action_button(
            "electricity_add_occupancy",
            "Add occupancy period",
            class_="btn-secondary",
        ),
        ui.input_date("electricity_through", "Forecast through"),
        ui.input_action_button(
            "electricity_forecast_btn",
            "Forecast electricity into cash flow",
            class_="btn-primary",
        ),
        ui.output_text("electricity_forecast_status"),
    )


def _occupancy_ranges(input, count: int):
    ranges = []
    for index in range(1, count + 1):
        start = input[f"electricity_occupied_from_{index}"]()
        end = input[f"electricity_occupied_through_{index}"]()
        ranges.append(validate_occupancy_dates(start, end))
    return ranges


def run_electricity_forecast(input, occupancy_count: int):
    """Run the existing engine using the upload and all occupancy periods."""
    usage_path = uploaded_file_path(input.electricity_usage_upload())
    ranges = _occupancy_ranges(input, occupancy_count)
    through = pd.Timestamp(input.electricity_through())
    if pd.isna(through):
        raise ValueError("Forecast through date is required")

    usage = pd.read_csv(usage_path)
    usage.columns = usage.columns.str.strip()
    usage["Billing From"] = pd.to_datetime(usage["Billing From"])
    usage["Billing To"] = pd.to_datetime(usage["Billing To"])
    weather_start = min(usage["Billing From"].min(), *(start for start, _ in ranges))
    weather_end = max(usage["Billing To"].max(), through, *(end for _, end in ranges))
    weather = build_average_weather(weather_start, weather_end)

    occupancy = pd.DataFrame({"Date": weather["Date"], "Occupied": 0})
    for start, end in ranges:
        occupancy.loc[occupancy["Date"].between(start.normalize(), end.normalize()), "Occupied"] = 1

    from cashflow.forecasting_engines.electricity_forecast_package.electricity_forecast import (
        ElectricityForecaster,
    )

    def occupancy_fn(current):
        current = pd.Timestamp(current).normalize()
        return int(any(start.normalize() <= current <= end.normalize() for start, end in ranges))

    rows = ElectricityForecaster().fit(weather, usage, occupancy).forecast(
        through,
        occupancy_fn=occupancy_fn,
    )
    return rows, forecast_to_cashflow_months(rows)


def electricity_forecast_server(input, output):
    forecast_months = reactive.Value({})
    status_value = reactive.Value("")
    occupancy_count = reactive.Value(1)

    @reactive.effect
    @reactive.event(input.electricity_add_occupancy)
    def add_occupancy_period():
        occupancy_count.set(occupancy_count.get() + 1)

    @output
    @render.ui
    def electricity_occupancy_periods():
        return ui.TagList(
            *[
                ui.div(
                    {"class": "border rounded p-2 mb-2"},
                    ui.strong(f"Occupancy period {index}"),
                    ui.input_date(
                        f"electricity_occupied_from_{index}",
                        "Start date",
                    ),
                    ui.input_date(
                        f"electricity_occupied_through_{index}",
                        "End date",
                    ),
                )
                for index in range(1, occupancy_count.get() + 1)
            ]
        )

    @reactive.effect
    @reactive.event(input.electricity_forecast_btn)
    def forecast():
        try:
            _, monthly = run_electricity_forecast(input, occupancy_count.get())
        except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
            forecast_months.set({})
            status_value.set(f"Forecast failed: {error}")
            return
        forecast_months.set(monthly)
        status_value.set(
            f"Electricity forecast loaded for {len(monthly)} cash-flow month(s)."
        )

    @output
    @render.text
    def status():
        return status_value()

    return forecast_months
