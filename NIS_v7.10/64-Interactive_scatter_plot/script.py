# IMPORTANT: 'limjob' must be imported like this (not from nor as)
import limjob
import json
import urllib.request
import time

def run(imgs: tuple[limjob.Image], Job: limjob.JobParam, macro: limjob.MacroParam, ctx: limjob.RunContext):
    
    x_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsX)
    y_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsY)
    size_values = list(Job.Detect_cells.Tables.Records.BinFillArea)
    circularity_values = list(Job.Detect_cells.Tables.Records.BinCircularity)
    
    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length")
    
    points = [{"x": x, "y": y, "size": size, "circularity": circularity} for x, y, size, circularity in zip(x_values, y_values, size_values, circularity_values)]
    
    RTForm = limjob.RuntimeForm(Job.PythonScript.serverPath, Job.PythonScript.TaskName)
    BASE_URL = RTForm.baseURL()
    routes = RTForm.routes()
    
    RTForm.ensureServerIsRunning()
    
    urlValue = f"{BASE_URL}{routes["value"]}"
    urlSelected = f"{BASE_URL}{routes["selected"]}"
    data = json.dumps({"value": points}).encode("utf-8")
    request = urllib.request.Request(
        urlValue,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    with urllib.request.urlopen(request) as response:
        response.read()
    
    xPointsSelected = []
    yPointsSelected = []
    if (Job.PythonScript.isRuntimeForm):
        while not ctx.shouldAbort:
            with urllib.request.urlopen(urlSelected, timeout=5) as response:
                dataSelected = json.loads(response.read().decode("utf-8"))
    
            selectedPoints = dataSelected.get("value")
    
            if isinstance(selectedPoints, list) and len(selectedPoints) > 0:
                print("Points:", selectedPoints)
                xPointsSelected = [point["x"] for point in selectedPoints]
                yPointsSelected = [point["y"] for point in selectedPoints]
                break
            
            time.sleep(1)
    else:
        xPointsSelected = x_values
        yPointsSelected = y_values
    
    Job.NewPointSet.PointSet.set(xPointsSelected, yPointsSelected)