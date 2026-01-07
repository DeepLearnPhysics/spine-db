#!/usr/bin/env python3
"""Dash UI for browsing SPINE production runs.

A simple web interface for filtering and browsing the SPINE runs database.

Usage:
    python -m spine_db.app --db sqlite:///spine_files.db
    python -m spine_db.app --db postgresql://user:pass@localhost/spine_dd --port 8050
"""

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output
from sqlalchemy import func

from .schema import SpineFile, get_engine, get_session

# Global database session (initialized in create_app())
db_session = None


def create_layout():
    """Create the Dash app layout."""
    return dbc.Container(
        [
            html.H1("SPINE Production Runs Browser", className="mt-4 mb-4"),
            html.Hr(),
            # Filters
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("SPINE Version"),
                            dcc.Dropdown(
                                id="version-filter",
                                placeholder="All versions",
                                clearable=True,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Model Name"),
                            dcc.Dropdown(
                                id="model-filter",
                                placeholder="All models",
                                clearable=True,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Dataset Name"),
                            dcc.Dropdown(
                                id="dataset-filter",
                                placeholder="All datasets",
                                clearable=True,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Limit"),
                            dcc.Dropdown(
                                id="limit-dropdown",
                                options=[
                                    {"label": "10", "value": 10},
                                    {"label": "25", "value": 25},
                                    {"label": "50", "value": 50},
                                    {"label": "100", "value": 100},
                                    {"label": "500", "value": 500},
                                ],
                                value=50,
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="mb-4",
            ),
            # Stats
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            id="total-runs",
                                            className="card-title",
                                        ),
                                        html.P(
                                            "Total Runs",
                                            className="card-text",
                                        ),
                                    ]
                                )
                            ]
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            id="filtered-runs",
                                            className="card-title",
                                        ),
                                        html.P(
                                            "Filtered Runs",
                                            className="card-text",
                                        ),
                                    ]
                                )
                            ]
                        ),
                        md=3,
                    ),
                ],
                className="mb-4",
            ),
            # Results table
            html.Div(
                [
                    dash_table.DataTable(
                        id="runs-table",
                        columns=[
                            {"name": "ID", "id": "id"},
                            {"name": "Run", "id": "run"},
                            {"name": "Subrun", "id": "subrun"},
                            {"name": "Events", "id": "num_events"},
                            {"name": "Event Range", "id": "event_range"},
                            {"name": "File", "id": "file_name"},
                            {"name": "SPINE", "id": "spine_version"},
                            {"name": "Model", "id": "model_name"},
                            {"name": "Created", "id": "created_at"},
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "minWidth": "100px",
                        },
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)",
                            }
                        ],
                        page_action="none",
                        tooltip_data=[],
                        tooltip_duration=None,
                    ),
                ]
            ),
        ],
        fluid=True,
    )


def create_app(db_url: str):
    """Create and configure the Dash app.

    Parameters
    ----------
    db_url : str
        Database connection string

    Returns
    -------
    app : dash.Dash
        Configured Dash application
    """
    global db_session

    # Initialize database session
    engine = get_engine(db_url)
    db_session = get_session(engine)

    # Create Dash app
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title="SPINE Runs Browser",
    )

    app.layout = create_layout()

    # Callback to populate filter dropdowns
    @app.callback(
        [
            Output("version-filter", "options"),
            Output("model-filter", "options"),
            Output("dataset-filter", "options"),
        ],
        [Input("version-filter", "id")],  # Dummy input to trigger on load
    )
    def update_filter_options(_):
        # Get unique values for each filter
        versions = (
            db_session.query(SpineFile.spine_version)
            .distinct()
            .filter(SpineFile.spine_version.isnot(None))
            .all()
        )
        models = (
            db_session.query(SpineFile.model_name)
            .distinct()
            .filter(SpineFile.model_name.isnot(None))
            .all()
        )
        datasets = (
            db_session.query(SpineFile.dataset_name)
            .distinct()
            .filter(SpineFile.dataset_name.isnot(None))
            .all()
        )

        version_options = [{"label": v[0], "value": v[0]} for v in versions if v[0]]
        model_options = [{"label": m[0], "value": m[0]} for m in models if m[0]]
        dataset_options = [{"label": d[0], "value": d[0]} for d in datasets if d[0]]

        return version_options, model_options, dataset_options

    # Callback to update table based on filters
    @app.callback(
        [
            Output("runs-table", "data"),
            Output("runs-table", "tooltip_data"),
            Output("total-runs", "children"),
            Output("filtered-runs", "children"),
        ],
        [
            Input("version-filter", "value"),
            Input("model-filter", "value"),
            Input("dataset-filter", "value"),
            Input("limit-dropdown", "value"),
        ],
    )
    def update_table(version, model, dataset, limit):
        # Build query
        query = db_session.query(SpineFile)

        # Apply filters
        if version:
            query = query.filter(SpineFile.spine_version == version)
        if model:
            query = query.filter(SpineFile.model_name == model)
        if dataset:
            query = query.filter(SpineFile.dataset_name == dataset)

        # Get total and filtered counts
        total_count = db_session.query(func.count(SpineFile.id)).scalar()
        filtered_count = query.count()

        # Order by created_at descending and limit
        runs = query.order_by(SpineFile.created_at.desc()).limit(limit).all()

        # Format data for table
        data = []
        tooltips = []
        for run in runs:
            # Format event range
            if run.event_min is not None and run.event_max is not None:
                event_range = f"{run.event_min}-{run.event_max}"
            else:
                event_range = "N/A"

            data.append(
                {
                    "id": run.id,
                    "run": run.run if run.run is not None else "N/A",
                    "subrun": run.subrun if run.subrun is not None else "N/A",
                    "num_events": (
                        run.num_events if run.num_events is not None else "N/A"
                    ),
                    "event_range": event_range,
                    "file_name": Path(run.file_path).name,
                    "spine_version": run.spine_version or "N/A",
                    "model_name": run.model_name or "N/A",
                    "created_at": run.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            # Tooltip shows full file path
            tooltips.append(
                {
                    "file_name": {"value": run.file_path, "type": "text"},
                }
            )

        return data, tooltips, str(total_count), str(filtered_count)

    return app
