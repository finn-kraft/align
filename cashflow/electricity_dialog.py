"""Shiny dialog for running electricity forecasts into cash flow."""

from __future__ import annotations

import pandas as pd
from shiny import reactive, render, ui

from cashflow.electricity_integration import (
    build_average_weather,
    forecast_to_cashflow_months,
    uploaded_file_path,
    validate_occupancy_dates,
)


def electricity_forecast_dialog_ui():
    return ui.div(
        ui.h4("Electricity forecast"),
        ui.p(
            "Upload historical usage and manage one or more occupancy periods. "
            "Weather uses the average highs and lows from the temperature history."
        ),
        ui.input_file("electricity_usage_upload", "Upload usage.csv", accept=[".csv"]),
        ui.input_action_button(
            "electricity_manage_occupancy",
            "Add or edit occupancy periods",
            class_="btn-secondary",
        ),
        ui.input_date("electricity_through", "Forecast through"),
        ui.input_action_button(
            "electricity_forecast_btn",
            "Add electricity forecast to cash flow",
            class_="btn-primary",
        ),
        ui.output_text("electricity_forecast_status"),
    )


def _occupancy_ranges(input, periods):
    ranges = []
    for index, period in enumerate(periods, start=1):
        start = period["start"]
        end = period["end"]
        if start is None or end is None:
            start = input[f"electricity_occupied_from_{index}"]()
            end = input[f"electricity_occupied_through_{index}"]()
        ranges.append(validate_occupancy_dates(start, end))
    return ranges


def run_electricity_forecast(input, periods):
    """Run the existing engine using the upload and all saved occupancy periods."""
    usage_path = uploaded_file_path(input.electricity_usage_upload())
    ranges = _occupancy_ranges(input, periods)
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


def electricity_forecast_server(input, output, on_forecast):
    """Manage the occupancy modal and notify cash flow after a successful forecast."""
    forecast_months = reactive.Value({})
    status_value = reactive.Value("")
    occupancy_periods = reactive.Value([{"start": None, "end": None}])

    def capture_periods():
        captured = []
        for index, period in enumerate(occupancy_periods.get(), start=1):
            start, end = period["start"], period["end"]
            try:
                current_start = input[f"electricity_occupied_from_{index}"]()
                current_end = input[f"electricity_occupied_through_{index}"]()
                start = current_start or start
                end = current_end or end
            except Exception:
                pass
            captured.append({"start": start, "end": end})
        return captured

    def show_occupancy_modal():
        periods = occupancy_periods.get()
        ui.modal_show(
            ui.modal(
                ui.h4("Occupancy periods"),
                ui.p("Add every date range when the home will be occupied."),
                *[
                    ui.div(
                        {"class": "border rounded p-2 mb-2"},
                        ui.strong(f"Occupancy period {index}"),
                        ui.input_date(
                            f"electricity_occupied_from_{index}",
                            "Start date",
                            value=period["start"],
                        ),
                        ui.input_date(
                            f"electricity_occupied_through_{index}",
                            "End date",
                            value=period["end"],
                        ),
                    )
                    for index, period in enumerate(periods, start=1)
                ],
                ui.input_action_button(
                    "electricity_add_occupancy",
                    "Add new period",
                    class_="btn-secondary",
                ),
                footer=ui.input_action_button(
                    "electricity_save_occupancy",
                    "Done",
                    class_="btn-primary",
                ),
                easy_close=True,
            )
        )

    @reactive.effect
    @reactive.event(input.electricity_manage_occupancy)
    def manage_occupancy():
        show_occupancy_modal()

    @reactive.effect
    @reactive.event(input.electricity_add_occupancy)
    def add_occupancy_period():
        occupancy_periods.set(capture_periods() + [{"start": None, "end": None}])
        show_occupancy_modal()

    @reactive.effect
    @reactive.event(input.electricity_save_occupancy)
    def save_occupancy_periods():
        periods = capture_periods()
        for period in periods:
            validate_occupancy_dates(period["start"], period["end"])
        occupancy_periods.set(periods)
        ui.modal_remove()

    @reactive.effect
    @reactive.event(input.electricity_forecast_btn)
    def forecast():
        try:
            _, monthly = run_electricity_forecast(input, occupancy_periods.get())
            on_forecast(monthly)
        except Exception as error:
            forecast_months.set({})
            status_value.set(f"Forecast failed: {error}")
            return
        forecast_months.set(monthly)
        status_value.set(
            f"Electricity forecast added to {len(monthly)} cash-flow month(s)."
        )

    @output
    @render.text
    def status():
        return status_value()

    return forecast_months
