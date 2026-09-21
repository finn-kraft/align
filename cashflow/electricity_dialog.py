"""Shiny dialog for running electricity forecasts into cash flow."""

from __future__ import annotations

from pathlib import Path

from shiny import ui, reactive, render

from cashflow.electricity_integration import (
    forecast_to_cashflow_months,
    validate_electricity_inputs,
)


def electricity_forecast_dialog_ui():
    return ui.div(
        ui.h4("Electricity forecast"),
        ui.p(
            "Provide the three historical datasets used by the electricity engine. "
            "The forecast will populate the Utilities field in matching cash-flow months."
        ),
        ui.input_text("electricity_weather_path", "Weather CSV path"),
        ui.input_text("electricity_usage_path", "Billing-period usage CSV path"),
        ui.input_text("electricity_occupancy_path", "Daily occupancy CSV path"),
        ui.input_date("electricity_through", "Forecast through", value=None),
        ui.input_action_button(
            "electricity_forecast_btn",
            "Forecast electricity into cash flow",
            class_="btn-primary",
        ),
        ui.output_text("electricity_forecast_status"),
    )


def run_electricity_forecast(input):
    """Run the existing engine and return its rows plus monthly cash-flow values."""
    weather, usage, occupancy, through = validate_electricity_inputs(
        input.electricity_weather_path(),
        input.electricity_usage_path(),
        input.electricity_occupancy_path(),
        input.electricity_through(),
    )
    # The package is intentionally kept isolated from the cash-flow model.
    from cashflow.forecasting_engines.electricity_forecast_package.electricity_forecast import (
        ElectricityForecaster,
    )

    forecaster = ElectricityForecaster()
    rows = forecaster.fit(weather, usage, occupancy).forecast(through)
    return rows, forecast_to_cashflow_months(rows)


def electricity_forecast_server(input, output):
    forecast_months = reactive.Value({})

    @reactive.effect
    @reactive.event(input.electricity_forecast_btn)
    def forecast():
        try:
            _, monthly = run_electricity_forecast(input)
        except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
            forecast_months.set({})
            status.set(f"Forecast failed: {error}")
            return
        forecast_months.set(monthly)
        status.set(
            f"Electricity forecast loaded for {len(monthly)} cash-flow month(s)."
        )

    @output
    @render.text
    def status():
        return ""

    return forecast_months
