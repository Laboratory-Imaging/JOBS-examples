from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Any

from bokeh.embed import components
from bokeh.models import ColumnDataSource, LassoSelectTool, Scatter
from bokeh.plotting import figure
from bokeh.resources import INLINE

app = FastAPI(title="External Form Example")

job_task_values: dict[str, Any] = {}
job_task_selected_values: dict[str, Any] = {}

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")


class ValueModel(BaseModel):
    value: Any


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/{job_task_id}/ui")
def external_form_ui(job_task_id: str, request: Request):
    theme_header = request.headers.get("x-app-color-scheme", "light").lower()
    theme = "dark" if theme_header == "dark" else "light"
    raw_points = job_task_values.get(job_task_id, [])

    points = []
    if isinstance(raw_points, list):
        for point in raw_points:
            if isinstance(point, dict) and "x" in point and "y" in point and "size" in point and "circularity" in point:
                points.append({"x": point["x"], "y": point["y"], "size": point["size"], "circularity": point["circularity"]})

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
        title=f"Select cells to image in hi mag {job_task_id}",
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
    plot_script, plot_div = components(plot)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "theme": theme,
            "job_task_id": job_task_id,
            "value_url": f"/{job_task_id}/value",
            "selected_url": f"/{job_task_id}/selected",
            "has_points": bool(points),
            "points_count": len(points),
            "plot_script": plot_script,
            "plot_div": plot_div,
            "bokeh_js": INLINE.render_js(),
            "bokeh_css": INLINE.render_css(),
        },
    )


@app.get("/{job_task_id}/value")
def get_value(job_task_id: str):
    return {"value": job_task_values.get(job_task_id, "")}


@app.post("/{job_task_id}/value")
def set_value(job_task_id: str, model: ValueModel):
    job_task_values[job_task_id] = model.value
    job_task_selected_values.pop(job_task_id, None)
    return {"status": "ok"}


@app.get("/{job_task_id}/selected")
def get_selected_value(job_task_id: str):
    return {"value": job_task_selected_values.get(job_task_id, "")}


@app.post("/{job_task_id}/selected")
def set_selected_value(job_task_id: str, model: ValueModel):
    job_task_selected_values[job_task_id] = model.value
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host = "127.0.0.2", port = 8080)
