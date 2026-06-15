"""
Main Dash application entry point for the Urban Mobility Equity Dashboard.

Run:
    python -m src.dashboard.app
then open http://127.0.0.1:8050 in a browser.

Requires that MES GeoJSONs exist under data/processed/mes_scores/ (produced by
the pipeline / notebook 06). If none are present the dashboard still launches
but the city dropdown will be empty.
"""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc

from src.dashboard.callbacks import register_callbacks
from src.dashboard.layout import create_layout

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Urban Mobility Equity Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server  # for gunicorn / deployment

app.layout = create_layout()
register_callbacks(app)


if __name__ == "__main__":
    # threaded=True so concurrent callbacks (map, equity gap, ranking all fire on
    # load) don't block one another on the single-threaded dev server.
    app.run(debug=True, port=8050, threaded=True)
