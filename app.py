from shiny import App, ui

from cashflow.cashflow import cashflow_ui, cashflow_server
from gas.gas_dashboard import gas_ui, gas_server


app_ui = ui.page_navbar(

    ui.nav_panel("Cash Flow", cashflow_ui()),

    ui.nav_panel("Gas Dashboard", gas_ui()),

    ui.nav_panel(
        "Expenses (Pillar 1)",
        ui.h3("Expense Tracking Engine"),
        ui.p("Coming soon...")
    ),

    ui.nav_panel(
        "Assets (Pillar 5)",
        ui.h3("Asset Modeling"),
        ui.p("Coming soon...")
    ),

    title="Align Financial System"
)


def server(input, output, session):
    cashflow_server(input, output, session)
    gas_server(input, output, session)


app = App(app_ui, server)