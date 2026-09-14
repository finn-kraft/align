from shiny import ui, render, reactive
from shinywidgets import render_plotly, output_widget
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from pathlib import Path

from .pipeline import ensure_processed_data, run_pipeline
from .series import rolling_average

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = Path(BASE_DIR) / "data"
LIVE_DATA_FILE = DATA_DIR / "live_data.csv"
DATA_FILE = DATA_DIR / "processed_data.csv"
REJECTED_FILE = DATA_DIR / "rejected_rows.csv"

# ----------------------------
# UI
# ----------------------------
def gas_ui():
    return ui.page_fluid(
        ui.h1("⛽ Fuel Efficiency & Cost Dashboard"),
        ui.card(
            ui.card_header("Gas data"),
            ui.p("Import a Google Sheet CSV export, or place the latest export at gas/data/live_data.csv."),
            ui.input_file("gas_source_file", "Import gas CSV", accept=[".csv"], multiple=False),
            ui.output_text("gas_import_status"),
        ),
        ui.output_text("data_quality_summary"),

        ui.hr(),
        ui.h3("MPG vs Odometer"),
        ui.output_text("efficiency_summary"),
        output_widget("efficiency_plot"),

        ui.hr(),
        ui.output_text("cost_summary"),
        ui.h3("💵 Fuel Cost per Mile Over Time"),
        output_widget("cost_plot"),

        ui.hr(),
        ui.output_text("monthly_summary"),
        ui.h3("Cost per Month"),
        output_widget("monthly_spend_plot"),

        ui.hr(),
        ui.output_table("data_preview")
    )

# ----------------------------
# SERVER
# ----------------------------
def gas_server(input, output, session):

    refresh = reactive.Value(0)
    import_status = reactive.Value("Checking for gas data…")

    @reactive.effect
    @reactive.event(input.gas_source_file)
    def import_gas_source():
        uploaded = input.gas_source_file()
        if not uploaded:
            return
        record = uploaded[0]
        try:
            result = run_pipeline(
                Path(record["datapath"]),
                DATA_FILE,
                REJECTED_FILE,
                source_name=f'upload:{record["name"]}',
                default_vehicle="2012 Volkswagen Jetta 2.5L SE",
            )
        except Exception as error:
            import_status.set(f"Import failed: {error}")
            return
        refresh.set(refresh.get() + 1)
        import_status.set(
            f"Imported {len(result.analytics_rows)} intervals; "
            f"rejected {len(result.rejected_rows)} rows; "
            f"flagged {len(result.quality_issues)} quality issues."
        )

    @output
    @render.text
    def gas_import_status():
        return import_status.get()

    @reactive.Calc
    def df():
        refresh.get()
        try:
            if LIVE_DATA_FILE.exists():
                refreshed = ensure_processed_data(
                    LIVE_DATA_FILE,
                    DATA_FILE,
                    REJECTED_FILE,
                    source_name="google-sheet:jetta",
                    default_vehicle="2012 Volkswagen Jetta 2.5L SE",
                )
                if refreshed:
                    import_status.set("Prepared the latest gas source export.")
            if not DATA_FILE.exists():
                import_status.set("No gas source is available. Import a CSV above.")
                return pd.DataFrame()
            d = pd.read_csv(DATA_FILE, parse_dates=["Timestamp"])
            if d.empty:
                import_status.set("The source was processed, but no valid intervals remain.")
            return d
        except Exception as error:
            import_status.set(f"Gas data could not be prepared: {error}")
            return pd.DataFrame()

    @output
    @render.text
    def data_quality_summary():
        d = df()
        if d.empty:
            return import_status.get()
        if "Quality Flags" not in d:
            return f"{len(d)} observations loaded. Reprocess data to add quality checks."
        flagged = d["Quality Flags"].fillna("").astype(str).str.strip().ne("").sum()
        reliable = d["TripMPG_clean"].notna().sum()
        return f"{len(d)} intervals loaded | {reliable} reliable MPG intervals | {flagged} flagged for review"

    # -------- Efficiency --------
    @output
    @render.text
    def efficiency_summary():
        d = df()
        if d.empty or "TripMPG_clean" not in d:
            return "No data"

        avg = d["TripMPG_clean"].mean()
        med = d["TripMPG_clean"].median()
        total_miles = d["MilesPerTank"].sum()
        std = d["TripMPG_clean"].std()

        rolling = d["TripMPG_clean"].rolling(5).mean().dropna()
        slope = rolling.iloc[-1] - rolling.iloc[-2] if len(rolling) >= 2 else 0
        arrow = "↑" if slope > 0 else "↓" if slope < 0 else "→"

        return f"Avg MPG: {avg:.2f} | Median: {med:.2f} | Std: {std:.1f} | Trend: {arrow} {slope:+.2f} | Miles: {total_miles:.0f}"

    # -------- Cost --------
    @output
    @render.text
    def cost_summary():
        d = df()
        if d.empty or "CostPerMile" not in d:
            return "No data"

        avg = d["CostPerMile"].mean()
        med = d["CostPerMile"].median()
        std = d["CostPerMile"].std()

        rolling = d["CostPerMile"].rolling(5).mean().dropna()
        slope = rolling.iloc[-1] - rolling.iloc[-2] if len(rolling) >= 2 else 0
        arrow = "↑" if slope > 0 else "↓" if slope < 0 else "→"

        return f"Avg $/mile: ${avg:.3f} | Median: ${med:.3f} | Std: ${std:.4f} | Trend: {arrow} {slope:+.4f}"

    # -------- Monthly --------
    @output
    @render.text
    def monthly_summary():
        d = df()
        if d.empty or "Total Cost" not in d:
            return "No data"

        d = d.copy()
        d["Date"] = pd.to_datetime(d["Timestamp"])
        d["YearMonth"] = d["Date"].dt.to_period("M")

        monthly = (
            d.groupby("YearMonth")
            .agg(
                TotalSpent=("Total Cost", "sum"),
                TotalMiles=("MilesPerTank", "sum"),
                TotalGallons=("Gallons", "sum")
            )
            .reset_index()
        )

        if monthly.empty:
            return "No monthly data"

        med = monthly["TotalSpent"].median()
        std = monthly["TotalSpent"].std()

        return f"Median Monthly: ${med:,.2f} | Std: ${std:,.2f}"

    # -------- Plot 1 --------
    @output
    @render_plotly
    def efficiency_plot():
        d = df()
        if d.empty:
            return

        plot_data = d.sort_values("Odometer").copy()
        plot_data["MPG Rolling Average"] = rolling_average(
            plot_data["TripMPG_clean"], window=5
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_data["Odometer"],
            y=plot_data["TripMPG_clean"],
            mode="lines+markers",
            name="Trip MPG",
            line={"width": 1},
            opacity=0.55,
        ))
        fig.add_trace(go.Scatter(
            x=plot_data["Odometer"],
            y=plot_data["MPG Rolling Average"],
            mode="lines",
            name="5-fill rolling average",
            line={"width": 4},
        ))
        return fig

    # -------- Plot 2 --------
    @output
    @render_plotly
    def cost_plot():
        d = df()
        if d.empty:
            return

        plot_data = d.sort_values("Timestamp").copy()
        plot_data["Cost Rolling Average"] = rolling_average(
            plot_data["CostPerMile"], window=5
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_data["Timestamp"],
            y=plot_data["CostPerMile"],
            mode="lines+markers",
            name="Cost/Mile",
            line={"width": 1},
            opacity=0.55,
        ))
        fig.add_trace(go.Scatter(
            x=plot_data["Timestamp"],
            y=plot_data["Cost Rolling Average"],
            mode="lines",
            name="5-fill rolling average",
            line={"width": 4},
        ))
        return fig

    # -------- Plot 3 --------
    @output
    @render_plotly
    def monthly_spend_plot():
        d = df()
        if d.empty:
            return

        d["Date"] = pd.to_datetime(d["Timestamp"])
        d["YearMonth"] = d["Date"].dt.to_period("M")

        monthly = d.groupby("YearMonth")["Total Cost"].sum().reset_index()
        monthly["Date"] = monthly["YearMonth"].dt.to_timestamp()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["Date"],
            y=monthly["Total Cost"],
            name="Monthly Spend"
        ))
        return fig

    # -------- Table --------
    @output
    @render.table
    def data_preview():
        d = df()
        return d.tail(10) if not d.empty else pd.DataFrame()