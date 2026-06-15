"""
Dash callbacks wiring the controls to the map, side panel, comparison chart,
ranking table, and downloads.
"""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dash_table, dcc, html, no_update

from src.config import CITIES
from src.dashboard import utils

SUB_COLS = ["transit_norm", "walk_norm", "bike_norm", "ev_norm"]


def _filter_gdf(gdf, mes_range, desert_filter):
    data = gdf[(gdf["MES"] >= mes_range[0]) & (gdf["MES"] <= mes_range[1])]
    if "desert" in (desert_filter or []) and "mobility_desert" in data.columns:
        data = data[data["mobility_desert"]]
    if "compound" in (desert_filter or []) and "compounded_desert" in data.columns:
        data = data[data["compounded_desert"]]
    return data


def register_callbacks(app: dash.Dash) -> None:

    @app.callback(
        Output("main-map", "figure"),
        Input("city-dropdown", "value"),
        Input("layer-dropdown", "value"),
        Input("mes-slider", "value"),
        Input("desert-filter", "value"),
    )
    def update_map(city_key, layer, mes_range, desert_filter):
        if not city_key:
            return no_update
        gdf = utils.load_city(city_key)
        data = _filter_gdf(gdf, mes_range, desert_filter)
        if data.empty:
            data = gdf
        return utils.choropleth(data, layer)

    @app.callback(
        Output("selected-geoid", "data"),
        Input("main-map", "clickData"),
        State("city-dropdown", "value"),
    )
    def store_click(click_data, city_key):
        if not click_data:
            return no_update
        idx = click_data["points"][0]["location"]
        gdf = utils.load_city(city_key)
        try:
            return str(gdf.loc[idx, "GEOID"])
        except KeyError:
            return no_update

    @app.callback(
        Output("side-panel", "children"),
        Input("selected-geoid", "data"),
        State("city-dropdown", "value"),
    )
    def update_side_panel(geoid, city_key):
        if not geoid or not city_key:
            return no_update
        gdf = utils.load_city(city_key)
        row = gdf[gdf["GEOID"] == geoid]
        if row.empty:
            return no_update
        row = row.iloc[0]
        medians = gdf[SUB_COLS].median()

        mes = row["MES"]
        pctile = row.get("MES_percentile", float("nan"))
        color = "#c0392b" if mes < 33 else "#e67e22" if mes < 66 else "#27ae60"

        demo = utils.load_demographics(city_key)
        demo_table = html.P("Demographic data unavailable (set CENSUS_API_KEY).",
                            className="text-muted small")
        if not demo.empty:
            d = demo[demo["GEOID"] == geoid]
            if not d.empty:
                d = d.iloc[0]
                demo_table = dbc.Table([
                    html.Tbody([
                        html.Tr([html.Td("Median income"),
                                 html.Td(f"${d.get('median_income', float('nan')):,.0f}")]),
                        html.Tr([html.Td("% non-white"),
                                 html.Td(f"{d.get('pct_nonwhite', float('nan')):.1f}%")]),
                        html.Tr([html.Td("% no vehicle"),
                                 html.Td(f"{d.get('pct_no_vehicle', float('nan')):.1f}%")]),
                        html.Tr([html.Td("% renter"),
                                 html.Td(f"{d.get('pct_renter', float('nan')):.1f}%")]),
                    ])
                ], bordered=False, size="sm")

        return [
            html.H5(f"Tract {geoid}"),
            html.H2(f"{mes:.1f}", style={"color": color}),
            html.P(f"Mobility Equity Score · Bottom {pctile:.0f}% of city"
                   if pctile == pctile else "Mobility Equity Score"),
            html.Hr(),
            dcc.Graph(figure=utils.subindex_bar(row, medians),
                      config={"displayModeBar": False}),
            dbc.Alert(utils.interpretation_text(row), color="warning"),
            html.H6("Demographics"),
            demo_table,
        ]

    @app.callback(
        Output("equity-gap", "figure"),
        Input("city-dropdown", "value"),
    )
    def update_equity_gap(_city_key):
        city_keys = [c["value"] for c in utils.available_cities()]
        return utils.equity_gap_figure(city_keys)

    @app.callback(
        Output("ranked-table", "children"),
        Input("city-dropdown", "value"),
        Input("rank-by", "value"),
    )
    def update_ranked_table(city_key, rank_by):
        if not city_key:
            return no_update
        gdf = utils.load_city(city_key)
        table = utils.ranked_table(gdf, rank_by)
        return dash_table.DataTable(
            data=table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in table.columns],
            style_cell={"fontSize": 12, "padding": "4px"},
            style_header={"fontWeight": "bold"},
            page_size=10,
        )

    @app.callback(
        Output("dl-csv", "data"),
        Input("btn-csv", "n_clicks"),
        State("city-dropdown", "value"),
        State("mes-slider", "value"),
        State("desert-filter", "value"),
        prevent_initial_call=True,
    )
    def download_filtered(_n, city_key, mes_range, desert_filter):
        gdf = utils.load_city(city_key)
        data = _filter_gdf(gdf, mes_range, desert_filter).drop(columns="geometry")
        return dcc.send_data_frame(data.to_csv, f"{city_key}_filtered.csv", index=False)

    @app.callback(
        Output("dl-rank-csv", "data"),
        Input("btn-rank-csv", "n_clicks"),
        State("city-dropdown", "value"),
        State("rank-by", "value"),
        prevent_initial_call=True,
    )
    def download_ranked(_n, city_key, rank_by):
        gdf = utils.load_city(city_key)
        table = utils.ranked_table(gdf, rank_by, n=50)
        return dcc.send_data_frame(table.to_csv, f"{city_key}_ranked_{rank_by}.csv", index=False)
