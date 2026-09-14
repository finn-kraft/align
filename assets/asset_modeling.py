"""Shiny UI for recording and inspecting vehicle total cost of ownership."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pandas as pd
from shiny import reactive, render, ui

from .vehicle_ownership import VehicleCostEvent
from .vehicle_repository import (
    create_vehicle, database_configured, delete_cost_event, delete_vehicle, delete_vehicle_and_costs,
    list_cost_events, list_vehicles, maintenance_breakdown, ownership_summaries,
    recent_repairs, record_cost_event, update_cost_event, update_vehicle,
)


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
    configured = database_configured()
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
                ui.input_action_button("save_vehicle", "Add vehicle", class_="btn-primary", disabled=not configured),
            ),
            ui.card(ui.card_header("Record an ownership cost"), ui.output_ui("vehicle_cost_form")),
        ),
        ui.card(ui.card_header("Total cost of ownership"), ui.output_table("ownership_summary")),
        ui.card(ui.card_header("Edit or delete records"), ui.output_ui("record_management")),
        ui.layout_columns(
            ui.card(ui.card_header("Maintenance by service"), ui.output_table("maintenance_table")),
            ui.card(ui.card_header("Repairs"), ui.output_table("repairs_table")),
        ),
    )


def asset_modeling_server(input, output, session):
    """Bind vehicle tracking forms to the restricted ownership repository."""
    refresh = reactive.Value(0)
    status = reactive.Value(
        "Add a vehicle to begin tracking its ownership costs."
        if database_configured()
        else "Vehicle persistence is not configured. Add ALIGN_DATABASE_URL to .env and restart Align."
    )

    @reactive.calc
    def vehicles():
        refresh.get()
        if not database_configured():
            return ()
        try:
            return list_vehicles()
        except RuntimeError as error:
            status.set(str(error))
            return ()

    def selected_managed_vehicle():
        """Return the vehicle selected in the record-management panel."""
        selected = input.manage_vehicle_id()
        return next((vehicle for vehicle in vehicles() if str(vehicle.id) == str(selected)), None)

    @reactive.calc
    def managed_costs():
        refresh.get()
        vehicle = selected_managed_vehicle()
        if vehicle is None:
            return ()
        try:
            return list_cost_events(vehicle.id)
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

    @output
    @render.ui
    def record_management():
        available = vehicles()
        if not available:
            return ui.p("Add a vehicle before managing records.")
        selected_id = str(input.manage_vehicle_id() or available[0].id)
        vehicle = next((item for item in available if str(item.id) == selected_id), available[0])
        costs = managed_costs() if str(vehicle.id) == selected_id else ()
        selected_cost_id = str(input.manage_cost_id() or "")
        selected_cost = next((item for item in costs if str(item["id"]) == selected_cost_id), costs[0] if costs else None)
        cost_choices = {
            str(item["id"]): f'{item["occurred_on"]} — {item["service_type"]} (${item["amount"]:,.2f})'
            for item in costs
        }
        return ui.TagList(
            ui.input_select("manage_vehicle_id", "Vehicle", choices={str(item.id): item.name for item in available}, selected=str(vehicle.id)),
            ui.h5("Vehicle details"),
            ui.layout_columns(
                ui.input_text("edit_vehicle_name", "Vehicle name", value=vehicle.name),
                ui.input_text("edit_vehicle_make", "Make", value=vehicle.make or ""),
                ui.input_text("edit_vehicle_model", "Model", value=vehicle.model or ""),
                ui.input_numeric("edit_vehicle_year", "Year", value=vehicle.year, min=1886, max=9999),
            ),
            ui.layout_columns(
                ui.input_date("edit_vehicle_acquired_on", "Acquired on", value=vehicle.acquired_on.isoformat()),
                ui.input_numeric("edit_vehicle_starting_odometer", "Starting odometer", value=float(vehicle.starting_odometer) if vehicle.starting_odometer is not None else None, min=0),
            ),
            ui.input_action_button("update_vehicle", "Save vehicle changes", class_="btn-primary"),
            ui.input_checkbox("confirm_delete_vehicle", "Confirm deletion of this empty vehicle", value=False),
            ui.input_action_button("delete_vehicle", "Delete empty vehicle", class_="btn-outline-danger ms-2"),
            ui.hr(),
            ui.h5("Delete all vehicle data"),
            ui.p("This permanently removes the vehicle and every linked ownership cost."),
            ui.input_text("delete_all_confirmation", f'Type “{vehicle.name}” to confirm'),
            ui.input_action_button("delete_all_vehicle_data", "Delete all vehicle data", class_="btn-danger"),
            ui.hr(),
            ui.h5("Ownership cost records"),
            ui.p("No cost records exist for this vehicle.") if selected_cost is None else ui.TagList(
                ui.input_select("manage_cost_id", "Cost record", choices=cost_choices, selected=str(selected_cost["id"])),
                ui.layout_columns(
                    ui.input_date("edit_cost_date", "Date", value=selected_cost["occurred_on"].isoformat()),
                    ui.input_select("edit_cost_category", "Category", choices=COST_CATEGORIES, selected=selected_cost["category"]),
                    ui.input_text("edit_cost_service", "Service or cost type", value=selected_cost["service_type"]),
                    ui.input_numeric("edit_cost_amount", "Amount", value=float(selected_cost["amount"]), min=0),
                ),
                ui.input_text_area("edit_cost_description", "Description", value=selected_cost["description"] or ""),
                ui.layout_columns(
                    ui.input_numeric("edit_cost_odometer", "Odometer", value=float(selected_cost["odometer"]) if selected_cost["odometer"] is not None else None, min=0),
                    ui.input_text_area("edit_cost_notes", "Notes", value=selected_cost["notes"] or ""),
                ),
                ui.input_action_button("update_cost", "Save cost changes", class_="btn-primary"),
                ui.input_checkbox("confirm_delete_cost", "Confirm deletion of this cost record", value=False),
                ui.input_action_button("delete_cost", "Delete cost record", class_="btn-outline-danger ms-2"),
            ),
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

    @reactive.effect
    @reactive.event(input.update_vehicle)
    def update_selected_vehicle():
        vehicle = selected_managed_vehicle()
        if vehicle is None:
            return
        try:
            year = input.edit_vehicle_year()
            update_vehicle(
                vehicle.id, name=input.edit_vehicle_name(), make=input.edit_vehicle_make(),
                model=input.edit_vehicle_model(), year=int(year) if year is not None else None,
                acquired_on=date.fromisoformat(str(input.edit_vehicle_acquired_on())),
                starting_odometer=input.edit_vehicle_starting_odometer(),
            )
        except Exception as error:
            ui.notification_show(str(error), type="error", duration=8)
            return
        refresh.set(refresh.get() + 1)
        ui.notification_show("Vehicle changes saved.", type="message", duration=5)

    @reactive.effect
    @reactive.event(input.delete_vehicle)
    def delete_empty_vehicle():
        vehicle = selected_managed_vehicle()
        if vehicle is None:
            return
        if not input.confirm_delete_vehicle():
            ui.notification_show("Confirm deletion before deleting the vehicle.", type="warning", duration=6)
            return
        try:
            delete_vehicle(vehicle.id)
        except Exception as error:
            ui.notification_show(str(error), type="error", duration=10)
            return
        refresh.set(refresh.get() + 1)
        ui.notification_show("Vehicle deleted.", type="message", duration=5)

    @reactive.effect
    @reactive.event(input.delete_all_vehicle_data)
    def delete_all_selected_vehicle_data():
        vehicle = selected_managed_vehicle()
        if vehicle is None:
            return
        try:
            delete_vehicle_and_costs(vehicle.id, input.delete_all_confirmation())
        except Exception as error:
            ui.notification_show(str(error), type="error", duration=10)
            return
        refresh.set(refresh.get() + 1)
        ui.notification_show("Vehicle and all linked ownership costs were deleted.", type="message", duration=8)

    def selected_managed_cost():
        selected = input.manage_cost_id()
        return next((item for item in managed_costs() if str(item["id"]) == str(selected)), None)

    @reactive.effect
    @reactive.event(input.update_cost)
    def update_selected_cost():
        existing = selected_managed_cost()
        if existing is None:
            return
        try:
            event = VehicleCostEvent(
                id=existing["id"], vehicle_id=existing["vehicle_id"],
                occurred_on=date.fromisoformat(str(input.edit_cost_date())),
                category=input.edit_cost_category(), service_type=input.edit_cost_service(),
                amount=Decimal(str(input.edit_cost_amount() or 0)),
                description=input.edit_cost_description(),
                odometer=Decimal(str(input.edit_cost_odometer())) if input.edit_cost_odometer() is not None else None,
                notes=input.edit_cost_notes(),
            )
            update_cost_event(event)
        except Exception as error:
            ui.notification_show(str(error), type="error", duration=8)
            return
        refresh.set(refresh.get() + 1)
        ui.notification_show("Cost record changes saved.", type="message", duration=5)

    @reactive.effect
    @reactive.event(input.delete_cost)
    def delete_selected_cost():
        existing = selected_managed_cost()
        if existing is None:
            return
        if not input.confirm_delete_cost():
            ui.notification_show("Confirm deletion before deleting the cost record.", type="warning", duration=6)
            return
        try:
            delete_cost_event(existing["vehicle_id"], existing["id"])
        except Exception as error:
            ui.notification_show(str(error), type="error", duration=8)
            return
        refresh.set(refresh.get() + 1)
        ui.notification_show("Cost record deleted.", type="message", duration=5)

    @output
    @render.table
    def ownership_summary():
        refresh.get()
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
        refresh.get()
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
        refresh.get()
        vehicle_id = selected_vehicle_id()
        if vehicle_id is None:
            return pd.DataFrame({"Status": ["Select a vehicle to see repairs separately from maintenance."]})
        try:
            rows = recent_repairs(vehicle_id)
        except Exception:
            return pd.DataFrame()
        return pd.DataFrame([{"Date": row["Date"], "Repair": row["Repair"], "Description": row["Description"], "Amount": f"${row['Amount']:,.2f}", "Odometer": row["Odometer"], "Notes": row["Notes"]} for row in rows])
