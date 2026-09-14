from shiny import ui, render, reactive
from shinywidgets import render_plotly, output_widget
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "processed_data.csv")

# ----------------------------
# UI
# ----------------------------
def gas_ui():
    return ui.page_fluid(
        ui.h1("⛽ Fuel Efficiency & Cost Dashboard"),\n        ui.output_text("data_quality_summary"),

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

    @reactive.Calc
    def df():
        if not os.path.exists(DATA_FILE):
            print("CSV not found")
            return pd.DataFrame()

        try:
            d = pd.read_csv(DATA_FILE, parse_dates=["Timestamp"])
            print("Loaded:", d.shape)
            return d
        except Exception as e:
            print("ERROR:", e)
            return pd.DataFrame()

    @output
    @render.text
    def data_quality_summary():
        d = df()
        if d.empty:
            return "No processed gas data. Run ./run gas first."
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

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=d["Odometer"],
            y=d["TripMPG_clean"],
            mode="lines+markers",
            name="Trip MPG"
        ))
        return fig

    # -------- Plot 2 --------
    @output
    @render_plotly
    def cost_plot():
        d = df()
        if d.empty:
            return

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=d["Timestamp"],
            y=d["CostPerMile"],
            mode="lines+markers",
            name="Cost/Mile"
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