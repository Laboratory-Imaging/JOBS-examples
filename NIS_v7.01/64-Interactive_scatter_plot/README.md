# Interactive scatter plot

This example demonstrates how to display a scatter plot in a web browser to let the user select by gating which cells to acquire in high magnification.

Specifically it:
1. **Captures** a low magnification image with cells
2. Uses **GA3** task to detect the cells, measure their features (position, size, circularity) and populate a JOBS parameter with the list.
3. The **Python Script** task then
    - sends the list of features to the server,
    - while waiting the user can select different tools to gate the desired cells,
    - after user clicks "Done" the filtered list is returned back to the python task and
    - fills the point set for high magnification acquisition
4. The **Point loop** iterates over the selected points and captures the cells in high magnification.

![Scatterplot](images/Scatterplot.png)

## Server

1. [Download](https://lim-public-af010c85-0d3e-4156-9378-5adc1bbef7b3.s3.eu-central-1.amazonaws.com/GitHubAssets/JOBS_Examples/NIS_v7.01/64-Interactive_scatter_plot/scatterplot_server.zip) and unzip the [server](./scatterplot_server/) files into a folder. For example:

```bat
%userprofile%\Documents\scatterplot_server
```

2. Prepare the python (Python 3.12) venv, activate it and install required libraries

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

3. Run it manually to see if it is working.

```bat
.venv\Scripts\activate.bat
python main.py --host 127.0.0.1 --port 8080
```

If everything was done correctly, you should see something like this in the command prompt:

![Starting the server](images/CMD%20-%20Server%20OK.png)

If you navigate to the [web page](http:127.0.0.1:8080/ui) you should see an empty scatterplot.
It is OK as it is the JOBS that populates the points.

## JOBS

This is the minimalistic [job](https://laboratory-imaging.github.io/JOBS-examples/NIS_v7.01/64-Interactive_scatter_plot/Server_Example.html)
[[Download link](https://lim-public-af010c85-0d3e-4156-9378-5adc1bbef7b3.s3.eu-central-1.amazonaws.com/GitHubAssets/JOBS_Examples/NIS_v7.01/64-Interactive_scatter_plot/Server_Example.bin)].

![JOB definition](images/Job%20definition.png)

The noteworthy parts is

- the GA3 and
- the Python Script

## GA3

The GA3 [recipe](https://laboratory-imaging.github.io/JOBS-examples/NIS_v7.01/64-Interactive_scatter_plot/Detect_cells.html)
[[Download link](https://lim-public-af010c85-0d3e-4156-9378-5adc1bbef7b3.s3.eu-central-1.amazonaws.com/GitHubAssets/JOBS_Examples/NIS_v7.01/64-Interactive_scatter_plot/Detect_cells.ga3)]
is simple too:

- Segmentation (Threshold) and
- Object measurement.

![Starting the server](images/GA3%20-%20Recipe.png)

The Object measurement node has:
- Object Circularity, Object Fill Area - for the gating and
- Object Center Abs - X, Y - stage coordinates for the point set.

![GA3 task](images/General%20Analysis%203%20task.png)

> [!IMPORTANT]
> Note the **column names** of relevant columns as they will be propagated to the JOBS parameter
> and then **Python Script task** uses these names to access the data.

## Python task

The node use the parameters (host, port and server_dir) to configure itself. Uncheck the blocking
checkbox so that the UI is responsible while waiting for user to select the points.

> [!NOTE]
> The Init value content is evaluated by python `eval()` function do string must be in `""`.

![Python Script task](images/PythonTask.png)

The script is the most important part. See the [whole script](script.py)

1. Retrieve the data from the JOBS parameter.

```python
def run(imgs: tuple[limjob.Image], Job: limjob.JobParam, macro: limjob.MacroParam, ctx: limjob.RunContext):
    x_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsX)
    y_values = list(Job.Detect_cells.Tables.Records.BinCenterAbsY)
    size_values = list(Job.Detect_cells.Tables.Records.BinFillArea)
    circularity_values = list(Job.Detect_cells.Tables.Records.BinCircularity)
```

2. Retrieve the node own parameters:

```python
    host, port = str(Job.PythonScript.host), int(Job.PythonScript.port)
    server_dir = Job.PythonScript.server_dir
    base_url = f"http://{host}:{port}"
```
3. Ensure the server in the `server_dir` is running using the `host` and the `port` provided in the parameters.

```python
    ensure_server_running(server_dir, base_url, host, port, ctx)
```

4. Serialize the data into json and send it to the server using `POST` method on `http://127.0.0.1:8080/value` endpoint.

```python
    points = [{"x": x, "y": y, "size": size, "circularity": circularity} for x, y, size, circularity in zip(x_values, y_values, size_values, circularity_values)]
    data = json.dumps({"value": points}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/value",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
```

5. Open the web page in default browser.

```python
    webbrowser.open(f"{base_url}/ui", 1)
```

6. Wait for the server response to the `GET` method on `http://127.0.0.1:8080/selected` endpoint.

```python
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
```

7. Fill the point set with the points returned from the server

```python
    Job.NewPointSet.PointSet.set(xPointsSelected, yPointsSelected)
```