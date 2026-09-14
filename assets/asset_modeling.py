"""Shiny UI for recording and inspecting vehicle total cost of ownership."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pandas as pd
from shiny import reactive, render, ui

from .vehicle_ownership import VehicleCostEvent
from .vehicle_repository import create_vehicle, list_vehicles, maintenance_breakdown, ownership_summaries, recent_repairs, record_cost_event


COST_CATEGORIES = {
    "purchase": "Purchase",
    "maintenance": "Maintenance (oil changes, tires, scheduled service)",
    "repair": "Repair (unexpected diagnosis or repair)",
    "administrative": "Administrative (insurance, registration, taxes)",
    "fuel": "Fuel",
    "other": "Other ownership cost",
}


def asset_modeling_ui():
    """Render a vehicle tracker with separate maintenance and repair records."""
    return ui.page_fluid(
        ui.h2("Asset Modeling — Vehicle Ownership"),
        ui.p("Track actual ownership cost. Purchase, maintenance, repairs, administrative costs, fuel, and other expenses remain separate."),
        ui.output_text("asset_status"),
        ui.layout_columns(
            ui.card(
                ui.card_header("Add a vehicle"),
                ui.input_text("vehicle_name", "Vehicle name", placeholder="e.g., 2014 Jetta"),
                ui.layout_columns(
                    ui.input_text("vehicle_make", "Make", placeholder="Volkswagen"),
                    ui.input_text("vehicle_model", "Model", placeholder="Jetta"),
                    ui.input_numeric("vehicle_year", "Year", value=None, min=1886, max=9999),
                    ui.input_date("vehicle_acquired_on", "Purchased/acquired on", value=date.today().isoformat()),
                ),
                ui.layout_columns(
                    ui.input_numeric("vehicle_purchase_price", "Purchase price", value=0, min=0),
                    ui.input_numeric("vehicle_starting_odometer", "Starting odometer", value=None, min=0),
                ),
                ui.input_action_button("save_vehicle", "Add vehicle", class_="btn-primary"),
            ),
            ui.card(ui.card_header("Record an ownership cost"), ui.output_ui("vehicle_cost_form")),
        ),
        ui.card(ui.card_header("Total cost of ownership"), ui.output_table("ownership_summary")),
        ui.layout_columns(
            ui.card(ui.card_header("Maintenance by service"), ui.output_table("maintenance_table")),
            ui.card(ui.card_header("Repairs"), ui.output_table("repairs_table")),
        ),
    )


def asset_modeling_server(input, output, session):
    """Bind vehicle tracking forms to the restricted ownership repository."""
    refresh = reactive.Value(0)
    status = reactive.Value("Add a vehicle to begin tracking its ownership costs.")

    @reactive.calc
    def vehicles():
        refresh.get()
        try:
            return list_vehicles()
        except RuntimeError as error:
            status.set(str(error))
            return ()
        except Exception:
            status.set("Asset data could not be loaded. Confirm the approved migration has been applied.")
            return ()

    @output
    @render.text
    def asset_status():
        return status.get()

    @output
    @render.ui
    def vehicle_cost_form():
        options = {str(vehicle.id): vehicle.name for vehicle in vehicles()}
        if not options:
            return ui.p("A vehicle must be saved before costs can be recorded.")
        return ui.TagList(
            ui.input_select("vehicle_cost_vehicle", "Vehicle", choices=options),
            ui.input_select("vehicle_cost_category", "Cost category", choices=COST_CATEGORIES, selected="maintenance"),
            ui.input_text("vehicle_cost_service", "Service or cost type", placeholder="e.g., Oil change, Tires, Insurance, Registration"),
            ui.input_text_area("vehicle_cost_description", "Description (optional)", placeholder="Vendor, work completed, or policy period"),
            ui.layout_columns(
                ui.input_date("vehicle_cost_date", "Date", value=date.today().isoformat()),
                ui.input_numeric("vehicle_cost_amount", "Amount", value=0, min=0),
                ui.input_numeric("vehicle_cost_odometer", "Odometer (optional)", value=None, min=0),
            ),
            ui.input_text_area("vehicle_cost_notes", "Notes (optional)"),
            ui.input_action_button("save_vehicle_cost", "Record cost", class_="btn-success"),
        )

    @reactive.effect
    @reactive.event(input.save_vehicle)
    def save_vehicle():
        try:
            year = input.vehicle_year()
            create_vehicle(
                name=input.vehicle_name(), make=input.vehicle_make(), model=input.vehicle_model(),
                year=int(year) if year is not None else None,
                acquired_on=date.fromisoformat(str(input.vehicle_acquired_on())),
                purchase_price=Decimal(str(input.vehicle_purchase_price() or 0)),
                starting_odometer=input.vehicle_starting_odometer(),
            )
        except (RuntimeError, ValueError) as error:
            status.set(str(error))
            ui.notification_show(str(error), type="error", duration=8)
            return
        except Exception as error:
            message = (
                "Vehicle was not saved. Confirm ALIGN_DATABASE_URL, migration 0002, "
                f"and the database role. ({type(error).__name__})"
            )
            status.set(message)
            ui.notification_show(message, type="error", duration=10)
            return
        refresh.set(refresh.get() + 1)
        message = "Vehicle saved. Its purchase price is included in total ownership cost."
        status.set(message)
        ui.notification_show(message, type="message", duration=5)

    @reactive.effect
    @reactive.event(input.save_vehicle_cost)
    def save_cost():
        try:
            event = VehicleCostEvent(
                vehicle_id=UUID(str(input.vehicle_cost_vehicle())),
                occurred_on=date.fromisoformat(str(input.vehicle_cost_date())),
                category=input.vehicle_cost_category(), service_type=input.vehicle_cost_service(),
                amount=Decimal(str(input.vehicle_cost_amount() or 0)),
                description=input.vehicle_cost_description(),
                odometer=Decimal(str(input.vehicle_cost_odometer())) if input.vehicle_cost_odometer() is not None else None,
                notes=input.vehicle_cost_notes(),
            )
            record_cost_event(event)
        except (RuntimeError, ValueError) as error:
            status.set(str(error))
            return
        except Exception:
            status.set("Cost was not saved. The database was not changed.")
            return
        refresh.set(refresh.get() + 1)
        status.set(f"Recorded {event.service_type} under {event.category}.")

    @output
    @render.table
    def ownership_summary():
        try:
            rows = ownership_summaries()
        except Exception:
            return pd.DataFrame({"Status": ["Vehicle summaries will appear after database setup."]})
        return pd.DataFrame([{
            "Vehicle": row.vehicle_name, "Total ownership cost": f"${row.total_cost:,.2f}",
            "Purchase": f"${row.purchase_cost:,.2f}", "Maintenance": f"${row.maintenance_cost:,.2f}",
            "Repairs": f"${row.repair_cost:,.2f}", "Administrative": f"${row.administrative_cost:,.2f}",
            "Fuel": f"${row.fuel_cost:,.2f}", "Other": f"${row.other_cost:,.2f}", "Events": row.event_count,
        } for row in rows])

    def selected_vehicle_id():
        value = input.vehicle_cost_vehicle()
        return UUID(str(value)) if value else None

    @output
    @render.table
    def maintenance_table():
        vehicle_id = selected_vehicle_id()
        if vehicle_id is None:
            return pd.DataFrame({"Status": ["Select a vehicle to see individual oil changes, tires, and other maintenance."]})
        try:
            rows = maintenance_breakdown(vehicle_id)
        except Exception:
            return pd.DataFrame()
        return pd.DataFrame([{"Service": row["Service"], "Events": row["Events"], "Total cost": f"${row['Total cost']:,.2f}"} for row in rows])

    @output
    @render.table
    def repairs_table():
        vehicle_id = selected_vehicle_id()
        if vehicle_id is None:
            return pd.DataFrame({"Status": ["Select a vehicle to see repairs separately from maintenance."]})
        try:
            rows = recent_repairs(vehicle_id)
        except Exception:
            return pd.DataFrame()
        return pd.DataFrame([{"Date": row["Date"], "Repair": row["Repair"], "Description": row["Description"], "Amount": f"${row['Amount']:,.2f}", "Odometer": row["Odometer"], "Notes": row["Notes"]} for row in rows])
