"""
Dashboard layout: header controls, map panel, side panel, comparison panel,
ranking sidebar, and download buttons. Built with dash-bootstrap-components.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.utils import available_cities

LAYER_OPTIONS = ["MES", "Transit", "Walkability", "Bicycle", "EV Charging"]
OVERLAY_OPTIONS = ["None", "Income Quintile", "% Non-White", "% No Vehicle", "% Renter"]


def _header() -> dbc.Card:
    cities = available_cities()
    default_city = cities[0]["value"] if cities else None
    return dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([
            html.Label("City", className="fw-bold"),
            dcc.Dropdown(id="city-dropdown", options=cities, value=default_city,
                         clearable=False),
        ], md=3),
        dbc.Col([
            html.Label("Map layer", className="fw-bold"),
            dcc.Dropdown(id="layer-dropdown",
                         options=[{"label": l, "value": l} for l in LAYER_OPTIONS],
                         value="MES", clearable=False),
        ], md=3),
        dbc.Col([
            html.Label("Demographic overlay", className="fw-bold"),
            dcc.Dropdown(id="overlay-dropdown",
                         options=[{"label": o, "value": o} for o in OVERLAY_OPTIONS],
                         value="None", clearable=False),
        ], md=3),
        dbc.Col([
            html.Label("Desert filter", className="fw-bold"),
            dcc.Checklist(id="desert-filter",
                          options=[{"label": " Mobility deserts only", "value": "desert"},
                                   {"label": " Compounded deserts only", "value": "compound"}],
                          value=[]),
        ], md=3),
    ])), className="mb-2")


def _map_panel() -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody([
        dcc.Graph(id="main-map", style={"height": "62vh"},
                  config={"displaylogo": False}),
        html.Div([
            html.Label("Filter tracts by MES range", className="fw-bold mt-2"),
            dcc.RangeSlider(id="mes-slider", min=0, max=100, step=1, value=[0, 100],
                            marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"}),
        ]),
    ])), md=8)


def _side_panel() -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody(id="side-panel", children=[
        html.H5("Click a tract on the map"),
        html.P("Select any census tract to see its Mobility Equity Score, "
               "sub-index breakdown, and demographic profile.",
               className="text-muted"),
    ])), md=4)


def _comparison_panel() -> dbc.Card:
    return dbc.Card(dbc.CardBody([
        html.H5("Equity gap — median MES by income quintile"),
        dcc.Graph(id="equity-gap", config={"displaylogo": False},
                  style={"height": "32vh"}),
    ]), className="mt-2")


def _ranking_panel() -> dbc.Card:
    return dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col(html.H5("Most disadvantaged tracts"), md=6),
            dbc.Col(dcc.Dropdown(
                id="rank-by",
                options=[{"label": f"Rank by {l}", "value": l} for l in LAYER_OPTIONS],
                value="MES", clearable=False), md=6),
        ]),
        html.Div(id="ranked-table"),
        dbc.ButtonGroup([
            dbc.Button("Download map (PNG)", id="btn-png", size="sm", color="secondary"),
            dbc.Button("Download filtered data (CSV)", id="btn-csv", size="sm", color="secondary"),
            dbc.Button("Download ranked list (CSV)", id="btn-rank-csv", size="sm", color="secondary"),
        ], className="mt-2"),
        dcc.Download(id="dl-csv"),
        dcc.Download(id="dl-rank-csv"),
    ]), className="mt-2")


def create_layout() -> dbc.Container:
    return dbc.Container([
        html.H3("Urban Mobility Equity Dashboard", className="mt-3"),
        html.P("How equitably is mobility infrastructure distributed across "
               "neighborhoods? Lower scores (darker red) indicate worse access.",
               className="text-muted"),
        _header(),
        dbc.Row([_map_panel(), _side_panel()]),
        _comparison_panel(),
        _ranking_panel(),
        dcc.Store(id="selected-geoid"),
        html.Footer("EMGT 7945 · Northeastern University · Data: Census ACS, "
                    "EPA SLD, OpenStreetMap, DOE AFDC, GTFS",
                    className="text-muted small my-3"),
    ], fluid=True)
