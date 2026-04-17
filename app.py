from shiny import App, ui

# Import your module
from cashflow import cashflow_ui, cashflow_server


# ----------------------------
# MAIN APP UI
# ----------------------------

app_ui = ui.page_navbar(

    ui.nav_panel(
        "Cash Flow",
        cashflow_ui()
    ),

    # --- Skeleton Sections (placeholders) ---
    ui.nav_panel(
        "Expenses (Pillar 1)",
        ui.h3("Expense Tracking Engine"),
        ui.p("Coming soon...")
    ),

    ui.nav_panel(
        "Value & Goals (Pillar 2)",
        ui.h3("Value Alignment Analytics"),
        ui.p("Coming soon...")
    ),

    ui.nav_panel(
        "Credit (Pillar 4)",
        ui.h3("Credit Optimization"),
        ui.p("Coming soon...")
    ),

    ui.nav_panel(
        "Assets (Pillar 5)",
        ui.h3("Asset Modeling"),
        ui.p("Coming soon...")
    ),

    title="Align Financial System"
)


# ----------------------------
# SERVER
# ----------------------------

def server(input, output, session):
    # Mount your cashflow server
    cashflow_server(input, output, session)


# ----------------------------
# APP
# ----------------------------

app = App(app_ui, server)