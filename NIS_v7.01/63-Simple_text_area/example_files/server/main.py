from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Any

app = FastAPI(title="External Form Example")

job_task_values: dict[str, Any] = {}

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class ValueModel(BaseModel):
    value: Any


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/{job_task_id}/external-form/ui")
def external_form_ui(job_task_id: str, request: Request):
    theme_header = request.headers.get("x-app-color-scheme", "light").lower()
    theme = "dark" if theme_header == "dark" else "light"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={ "theme": theme }
    )


@app.get("/{job_task_id}/external-form/value")
def get_value(job_task_id: str):
    return {"value": job_task_values.get(job_task_id, "")}


@app.post("/{job_task_id}/external-form/value")
def set_value(job_task_id: str, model: ValueModel):
    job_task_values[job_task_id] = model.value
    return {"status": "ok"}