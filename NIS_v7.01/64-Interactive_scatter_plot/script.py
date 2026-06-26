# IMPORTANT: 'limjob' must be imported like this (not from nor as)
import limjob
import json
import os
import subprocess
import urllib.request
import urllib.error
import time
import webbrowser
from pathlib import Path


def server_is_running(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
            if response.status != 200:
                return False
            data = json.loads(response.read().decode("utf-8"))
            return data.get("status") == "ok"
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def start_server(server_dir_: str, host: str, port: int):
    server_dir = Path(os.path.expandvars(server_dir_))
    activate_script = server_dir / ".venv" / "Scripts" / "activate.bat"
    main_script = server_dir / "main.py"

    if not activate_script.exists():
        raise FileNotFoundError(f"Server venv activate script was not found: {activate_script}")
    if not main_script.exists():
        raise FileNotFoundError(f"Server main.py was not found: {main_script}")

    command = f'call {activate_script} && python {main_script} --host {host} --port {port}'
    print(command)
    subprocess.Popen(
        ["cmd.exe", "/c", command],
        cwd=server_dir
    )


def ensure_server_running(server_dir: str, base_url: str, host: str, port: int, ctx: limjob.RunContext):
    if server_is_running(base_url):
        return

    start_server(server_dir, host, port)
    deadline = time.time() + 30
    while time.time() < deadline and not ctx.shouldAbort:
        if server_is_running(base_url):
            return
        time.sleep(1)

    raise RuntimeError(f"Scatterplot server did not start at {base_url}")

def run(imgs: tuple[limjob.Image], Job: limjob.JobParam, macro: limjob.MacroParam, ctx: limjob.RunContext):
    x_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsX)
    y_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsY)
    size_values = list(Job.Detect_cells.Tables.Records.BinFillArea)
    circularity_values = list(Job.Detect_cells.Tables.Records.BinCircularity)

    host, port = str(Job.PythonScript.host), int(Job.PythonScript.port)
    server_dir = Job.PythonScript.server_dir
    base_url = f"http://{host}:{port}"

    ensure_server_running(server_dir, base_url, host, port, ctx)

    points = [{"x": x, "y": y, "size": size, "circularity": circularity} for x, y, size, circularity in zip(x_values, y_values, size_values, circularity_values)]
    data = json.dumps({"value": points}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/value",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    webbrowser.open(f"{base_url}/ui", 1)

    with urllib.request.urlopen(request) as response:
        response.read()

    xPointsSelected = []
    yPointsSelected = []

    while not ctx.shouldAbort:
        with urllib.request.urlopen(f"{base_url}/selected", timeout=5) as response:
            dataSelected = json.loads(response.read().decode("utf-8"))

        selectedPoints = dataSelected.get("value")

        if isinstance(selectedPoints, list) and len(selectedPoints) > 0:
            print("Points:", selectedPoints)
            xPointsSelected = [point["x"] for point in selectedPoints]
            yPointsSelected = [point["y"] for point in selectedPoints]
            break

        time.sleep(1)

    Job.NewPointSet.PointSet.set(xPointsSelected, yPointsSelected)
