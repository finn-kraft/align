from shiny import ui, render, reactive
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json
from pathlib import Path
from cashflow.month_state import ensure_month_defaults
from cashflow.projection import generate_month_sequence, run_projection as calculate_projection
from cashflow.saved_run_repository import save_run
from cashflow.saved_runs import build_saved_run_snapshot
from cashflow.electricity_dialog import electricity_forecast_dialog_ui, electricity_forecast_server
from cashflow.electricity_integration import merge_electricity_into_month_inputs
# ----------------------------
# Constants
# ----------------------------

BASE_DIR = Path(__file__).parent
SAVE_DIR = BASE_DIR / "saves"
SAVE_DIR.mkdir(exist_ok=True)

SAVE_FILE = SAVE_DIR / "cash_simulator_save.json"

# ----------------------------
# Core Simulation Logic
# ----------------------------

def build_simulation_state(input):
    return {
        "months": input.months(),
        "start_month": input.start_month(),
        "starting_cash": input.starting_cash(),
        "apy": input.apy(),
        "recurring": {
            "rent": input.rent(),
            "food": input.food(),
            "phone": input.phone(),
            "internet": input.internet(),
        }
    }


def extract_month_inputs(input, key):
    def safe_get(field):
        input_id = f"{field}_{key}"
        try:
            value = input[input_id]()
            return value if value is not None else 0
        except Exception:
            return 0

    return {
        "income": safe_get("income"),
        "insurance": safe_get("insurance"),
        "utilities": safe_get("utilities"),
        "gas": safe_get("gas"),
        "clothing": safe_get("clothing"),
        "fun": safe_get("fun"),
        "eating_out": safe_get("eating_out"),
        "giving": safe_get("giving"),
        "car_repair": safe_get("car_repair"),
        "other_amount": safe_get("other_amount"),
    }


def collect_month_inputs(input, state):
    """Collect editable values for persistence without changing forecast logic."""
    collected = {}
    for month in generate_month_sequence(state["start_month"], state["months"]):
        key = month["key"]
        values = extract_month_inputs(input, key)
        input_id = f"other_label_{key}"
        try:
            values["other_label"] = input[input_id]() or ""
        except Exception:
            values["other_label"] = ""
        collected[key] = values
    return collected


def run_projection(state, input):
    """Adapt current Shiny inputs to the framework-independent projection."""
    monthly_inputs = {
        month["key"]: extract_month_inputs(input, month["key"])
        for month in generate_month_sequence(state["start_month"], state["months"])
    }
    return calculate_projection(state, monthly_inputs)


def default_month_data():
    return {
        "income": 0,
        "insurance": 0,
        "utilities": 0,
        "gas": 0,
        "clothing": 0,
        "fun": 0,
        "eating_out": 0,
        "giving": 0,
        "car_repair": 0,
        "other_label": "",
        "other_amount": 0,
    }


def build_month_card(key, label, data):
    return ui.column(
        6,
        ui.card(
            ui.h5(label),
            ui.input_numeric(f"income_{key}", "Income", data["income"]),
            ui.hr(),
            ui.input_numeric(f"insurance_{key}", "Insurance", data["insurance"]),
            ui.input_numeric(f"utilities_{key}", "Utilities", data["utilities"]),
            ui.input_numeric(f"gas_{key}", "Gas", data["gas"]),
            ui.input_numeric(f"clothing_{key}", "Clothing", data["clothing"]),
            ui.input_numeric(f"fun_{key}", "Fun", data["fun"]),
            ui.input_numeric(f"eating_out_{key}", "Eating Out", data["eating_out"]),
            ui.input_numeric(f"giving_{key}", "Giving", data["giving"]),
            ui.input_numeric(f"car_repair_{key}", "Car Repair", data["car_repair"]),
            ui.hr(),
            ui.input_text(f"other_label_{key}", "Other (Description)", data["other_label"]),
            ui.input_numeric(f"other_amount_{key}", "Other Amount", data["other_amount"]),
        )
    )


def write_save_file(data):
    print("Saving to:", SAVE_FILE)
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def read_save_file():
    if not SAVE_FILE.exists():
        return None
    with open(SAVE_FILE, "r") as f:
        return json.load(f)

# ----------------------------
# UI FUNCTION (IMPORTANT)
# ----------------------------

def cashflow_ui():
    return ui.div(
        ui.h2("Cash Flow Simulator"),
        ui.p(
            "Model a future cash position, then save an immutable run when the "
            "assumptions are ready to compare with actual results."
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h5("Model settings"),
                ui.input_numeric("starting_cash", "Starting cash", 0),
                ui.input_numeric("months", "Months to project", 12),
                ui.input_select(
                    "start_month",
                    "Starting month",
                    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                ),
                ui.input_numeric("apy", "Savings APY (%)", 3.3),
                ui.hr(),
                ui.h5("Recurring monthly expenses"),
                ui.input_numeric("rent", "Rent", 750),
                ui.input_numeric("food", "Food", 400),
                ui.input_numeric("phone", "Phone", 13),
                ui.input_numeric("internet", "Internet", 30),
                ui.hr(),
                ui.h5("Projection actions"),
                ui.input_action_button("run_sim", "Run projection", class_="btn-primary w-100"),
                ui.hr(),
                ui.h5("Save this run"),
                ui.input_text("run_name", "Run name", placeholder="e.g., Conservative winter plan"),
                ui.input_text_area("run_notes", "Notes (optional)", placeholder="What does this scenario represent?"),
                ui.input_action_button("save_btn", "Save run", class_="btn-success w-100"),
                ui.output_text("save_status"),
                ui.hr(),
                ui.input_action_button("load_btn", "Load local draft", class_="w-100"),
            ),
            ui.div(
                ui.card(electricity_forecast_dialog_ui()),
                ui.tags.details(
                    {"open": "open"},
                    ui.tags.summary(ui.strong("Monthly inputs")),
                    ui.div({"class": "pt-3"}, ui.output_ui("monthly_inputs")),
                ),
                ui.tags.details(
                    {"open": "open"},
                    ui.tags.summary(ui.strong("Projection results")),
                    ui.div(
                        {"class": "pt-3"},
                        ui.h4("Projection"),
                        ui.output_table("projection_table"),
                        ui.output_plot("balance_plot"),
                    ),
                ),
            ),
        ),
    )

# ----------------------------
# SERVER FUNCTION (IMPORTANT)
# ----------------------------

def cashflow_server(input, output, session):
    electricity_months = electricity_forecast_server(input, output)


    month_data = reactive.Value({})

    @reactive.effect
    @reactive.event(input.start_month, input.months)
    def ensure_month_data():
        month_sequence = generate_month_sequence(input.start_month(), input.months())
        updated, changed = ensure_month_defaults(
            month_data.get(),
            [month["key"] for month in month_sequence],
            default_month_data,
        )
        if changed:
            month_data.set(updated)

    @output
    @render.ui
    def monthly_inputs():

        month_sequence = generate_month_sequence(input.start_month(), input.months())
        stored = month_data.get()

        rows, current_row = [], []

        for month in month_sequence:
            key, label = month["key"], month["label"]
            data = stored.get(key, default_month_data())
            current_row.append(build_month_card(key, label, data))

            if len(current_row) == 2:
                rows.append(ui.row(*current_row))
                current_row = []

        if current_row:
            rows.append(ui.row(*current_row))

        return ui.TagList(*rows) 
    
    @reactive.calc
    @reactive.event(input.run_sim)
    def simulation():
        state = build_simulation_state(input)
        monthly_inputs = collect_month_inputs(input, state)
        monthly_inputs = merge_electricity_into_month_inputs(monthly_inputs, electricity_months.get())
        projection = calculate_projection(state, monthly_inputs)
        return pd.DataFrame(projection)
    
    @output
    @render.table
    def projection_table():
        df = simulation()
        return df if not df.empty else pd.DataFrame({"Status": ["Click 'Run Simulation'"]})

    @output
    @render.plot
    def balance_plot():
        df = simulation()

        fig, ax = plt.subplots()

        if not df.empty:
            ax.plot(range(len(df)), df["Ending Balance"])
            ax.set_xticks(range(len(df)))
            ax.set_xticklabels(df["Month"])

        return fig

    save_status_value = reactive.Value("")

    @output
    @render.text
    def save_status():
        return save_status_value()

    @reactive.effect
    @reactive.event(input.save_btn)
    def save_scenario():
        state = build_simulation_state(input)
        monthly_inputs = collect_month_inputs(input, state)
        monthly_inputs = collect_month_inputs(input, state)
        monthly_inputs = merge_electricity_into_month_inputs(monthly_inputs, electricity_months.get())
        projection = calculate_projection(state, monthly_inputs)

        try:
            snapshot = build_saved_run_snapshot(
                name=input.run_name(),
                notes=input.run_notes(),
                state=state,
                monthly_inputs=monthly_inputs,
                projection=projection,
            )
            save_run(snapshot)
        except (RuntimeError, ValueError) as error:
            save_status_value.set(str(error))
            return
        except Exception:
            save_status_value.set("Unable to save this run. The database was not changed.")
            return

        save_status_value.set(f"Saved run {snapshot.id}.")

    @reactive.effect
    @reactive.event(input.load_btn)
    def load_scenario():

        data = read_save_file()

        if not data:
            save_status_value.set("No save file found.")
            return

        session.send_input_message("starting_cash", {"value": data["starting_cash"]})
        session.send_input_message("months", {"value": data["months"]})
        session.send_input_message("start_month", {"value": data["start_month"]})
        session.send_input_message("apy", {"value": data["apy"]})

        for field, value in data["recurring"].items():
            session.send_input_message(field, {"value": value})

        month_data.set(data["months_data"])

        for key, month_values in data["months_data"].items():
            for field, value in month_values.items():
                session.send_input_message(f"{field}_{key}", {"value": value})

        save_status_value.set("Loaded successfully.")