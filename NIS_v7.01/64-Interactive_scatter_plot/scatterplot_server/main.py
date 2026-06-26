from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Any

from bokeh.embed import json_item
from bokeh.models import ColumnDataSource, LassoSelectTool, Scatter
from bokeh.plotting import figure
from bokeh.resources import INLINE
from pydantic import BaseModel

app = FastAPI(title="Interactive Scatter Plot Example")

current_value: Any = ""
selected_value: Any = ""

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ValueModel(BaseModel):
    value: Any


def valid_points(raw_points: Any) -> list[dict[str, Any]]:
    points = []
    if isinstance(raw_points, list):
        for point in raw_points:
            if isinstance(point, dict) and "x" in point and "y" in point and "size" in point and "circularity" in point:
                points.append({"x": point["x"], "y": point["y"], "size": point["size"], "circularity": point["circularity"]})
    return points


def create_plot(points: list[dict[str, Any]]):
    source = ColumnDataSource(
        data={
            "x": [point["x"] for point in points],
            "y": [point["y"] for point in points],
            "size": [point["size"] for point in points],
            "circularity": [point["circularity"] for point in points],
        },
        name="points_source",
    )
    lasso_select = LassoSelectTool()
    plot = figure(
        title="Detected cells",
        x_axis_label="Size",
        y_axis_label="Circularity",
        sizing_mode="stretch_width",
        height=420,
        tools=["pan", "wheel_zoom", "box_zoom", "tap", lasso_select, "reset", "save"],
    )
    renderer = plot.scatter("size", "circularity", source=source, size=9, color="#1f77b4", alpha=0.8)
    renderer.selection_glyph = Scatter(x="size", y="circularity", size=12, fill_color="#d62728", line_color="#d62728", fill_alpha=1.0, line_alpha=1.0)
    renderer.nonselection_glyph = Scatter(x="size", y="circularity", size=9, fill_color="#1f77b4", line_color="#1f77b4", fill_alpha=0.18, line_alpha=0.18)
    plot.toolbar.active_drag = lasso_select
    return plot


@app.get("/health", description="Returns a simple status response so clients can check that the server is running.")
def health():
    return {"status": "ok"}


@app.get("/ui", description="Returns the static HTML page that displays the interactive scatter plot.")
def external_form_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/bokeh.js", description="Returns the Bokeh JavaScript bundle needed by the static scatter plot page.")
def bokeh_js():
    return Response(content="\n".join(INLINE.js_raw), media_type="application/javascript")


@app.get("/plot", description="Returns the Bokeh plot JSON that the static page embeds into the browser.")
def get_plot():
    return json_item(create_plot(valid_points(current_value)), "plot")


@app.get("/value", description="Returns the complete point set currently stored on the server.")
def get_value():
    return {"value": current_value}


@app.post("/value", description="Stores a new complete point set and clears the previously selected points.")
def set_value(model: ValueModel):
    global current_value, selected_value
    current_value = model.value
    selected_value = ""
    return {"status": "ok"}


@app.get("/selected", description="Returns the point set selected by the user in the scatter plot.")
def get_selected_value():
    return {"value": selected_value}


@app.post("/selected", description="Stores the point set selected by the user in the scatter plot.")
def set_selected_value(model: ValueModel):
    global selected_value
    selected_value = model.value
    return {"status": "ok"}


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the interactive scatter plot server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
