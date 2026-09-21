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
            "Upload historical usage, then enter the date range for which the home "
            "will be occupied. Weather uses the average highs and lows from the "
            "temperature history."
        ),
        ui.input_file("electricity_usage_upload", "Upload usage.csv", accept=[".csv"]),
        ui.input_date("electricity_occupied_from", "Occupancy start date"),
        ui.input_date("electricity_occupied_through", "Occupancy end date"),
        ui.input_date("electricity_through", "Forecast through"),
        ui.input_action_button(
            "electricity_forecast_btn",
            "Forecast electricity into cash flow",
            class_="btn-primary",
        ),
        ui.output_text("electricity_forecast_status"),
    )


def run_electricity_forecast(input):
    """Run the existing engine using the dialog's upload and dates."""
    usage_path = uploaded_file_path(input.electricity_usage_upload())
    occupied_from, occupied_through = validate_occupancy_dates(
        input.electricity_occupied_from(),
        input.electricity_occupied_through(),
    )
    through = pd.Timestamp(input.electricity_through())
    usage = pd.read_csv(usage_path)
    usage.columns = usage.columns.str.strip()
    usage["Billing From"] = pd.to_datetime(usage["Billing From"])
    usage["Billing To"] = pd.to_datetime(usage["Billing To"])
    weather_start = min(usage["Billing From"].min(), occupied_from)
    weather_end = max(usage["Billing To"].max(), through)
    weather = build_average_weather(weather_start, weather_end)
    occupancy = build_occupancy_schedule(
        weather_start,
        weather_end,
        occupied_from,
        occupied_through,
    )

    from cashflow.forecasting_engines.electricity_forecast_package.electricity_forecast import (
        ElectricityForecaster,
    )

    forecaster = ElectricityForecaster()
    rows = forecaster.fit(weather, usage, occupancy).forecast(
        through,
        occupancy_fn=lambda current: int(
            occupied_from.normalize() <= pd.Timestamp(current).normalize()
            <= occupied_through.normalize()
        ),
    )
    return rows, forecast_to_cashflow_months(rows)


def electricity_forecast_server(input, output):
    forecast_months = reactive.Value({})
    status_value = reactive.Value("")

    @reactive.effect
    @reactive.event(input.electricity_forecast_btn)
    def forecast():
        try:
            _, monthly = run_electricity_forecast(input)
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
