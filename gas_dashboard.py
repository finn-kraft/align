from shiny import ui, render, reactive
from shinywidgets import render_plotly, output_widget
import pandas as pd
import plotly.graph_objects as go
import os
import subprocess
import threading

# ----------------------------
# PATHS (module-safe)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "data", "processed_data.csv")
GET_SCRIPT = os.path.join(BASE_DIR, "getCurrentData.py")
PROCESS_SCRIPT = os.path.join(BASE_DIR, "process_data.py")


# ----------------------------
# UI
# ----------------------------
def gas_ui():
    return ui.page_fluid(
        ui.h1("⛽ Gas Dashboard"),
        ui.input_action_button("refresh", "Refresh Data"),

        ui.hr(),
        ui.output_text("efficiency_summary"),
        output_widget("efficiency_plot"),

        ui.hr(),
        ui.output_text("cost_summary"),
        output_widget("cost_plot"),

        ui.hr(),
        ui.output_table("data_preview")
    )


# ----------------------------
# SERVER
# ----------------------------
def gas_server(input, output, session):

    running = False
    refresh_trigger = reactive.Value(0)

    # ---- pipeline runner ----
    def run_pipeline():
        nonlocal running

        if running:
            print("⏳ Pipeline already running, skipping")
            return

        running = True

        def task():
            nonlocal running
            try:
                subprocess.run(["python", "-u", GET_SCRIPT], check=True)
                subprocess.run(["python", "-u", PROCESS_SCRIPT], check=True)
                print("✅ Gas data updated")

                # trigger UI refresh
                refresh_trigger.set(refresh_trigger.get() + 1)

            except Exception as e:
                print("❌ Pipeline error:", e)
            finally:
                running = False

        threading.Thread(target=task, daemon=True).start()

    # ---- startup run ----
    @reactive.Effect
    def _startup():
        run_pipeline()

    # ---- manual refresh ----
    @reactive.Effect
    @reactive.event(input.refresh)
    def _manual():
        run_pipeline()

    # ---- auto refresh every 2 min ----
    @reactive.Effect
    def _auto():
        reactive.invalidate_later(120_000)
        run_pipeline()

    # ---- data loader ----
    @reactive.Calc
    def df():
        refresh_trigger.get()  # dependency trigger

        if not os.path.exists(DATA_FILE):
            print("⚠️ Missing:", DATA_FILE)
            return pd.DataFrame()

        try:
            return pd.read_csv(DATA_FILE, parse_dates=["Timestamp"])
        except Exception as e:
            print("❌ Load error:", e)
            return pd.DataFrame()

    # ---- outputs ----
    @output
    @render.text
    def efficiency_summary():
        d = df()
        if d.empty or "TripMPG_clean" not in d:
            return "No data"

        return f"Avg MPG: {d['TripMPG_clean'].mean():.2f}"

    @output
    @render_plotly
    def efficiency_plot():
        d = df()
        if d.empty:
            return

        fig = go.Figure()
        fig.add_scatter(x=d["Odometer"], y=d["TripMPG_clean"])
        return fig

    @output
    @render.text
    def cost_summary():
        d = df()
        if d.empty or "CostPerMile" not in d:
            return "No data"

        return f"Avg $/mile: {d['CostPerMile'].mean():.3f}"

    @output
    @render_plotly
    def cost_plot():
        d = df()
        if d.empty:
            return

        fig = go.Figure()
        fig.add_scatter(x=d["Timestamp"], y=d["CostPerMile"])
        return fig

    @output
    @render.table
    def data_preview():
        d = df()
        return d.tail(10) if not d.empty else pd.DataFrame()