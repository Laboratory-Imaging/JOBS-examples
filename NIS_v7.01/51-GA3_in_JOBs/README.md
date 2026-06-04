# GA3 in JOBS

This page provides guidance on which JOBs GA3 task to use in which situation. Combined with the JOBs storage model there are same
advantages and disadvantages with each approach.

## Overview

| JOBs task     | Storage     | Capabilities and limitations |
| ------------- | ----------- | --- |
| During acquisition | Database    | - table data accessible by the JOB for decision making<br>- tables go into the JOBS system tables or special GA3 tables<br>- all records from multiple ND2 are concatenated<br>- statistics only on data available at task execution<br>- CANNOT show GA3 results (graphs)<br>- CANNOT use `HDF5concatenate` |
| | Alternative | - table data accessible by the JOB for decision making<br>- tables go into H5 sidecar files (each ND2 has corresponding H5)<br>- all GA3 results available and shown when ND2 opens<br>- CANNOT use `HDF5concatenate` |
| After acquisition | Database    | - tables go into the JOBS system tables or special GA3 tables<br>- all records from multiple ND2 are concatenated<br>- CANNOT show GA3 results (graphs)<br>- can use `HDF5concatenate` to aggregate ALL data |
| | Alternative | - tables go into H5 sidecar files (each ND2 has corresponding H5)<br>- all GA3 results available and shown when ND2 opens<br>- can use `HDF5concatenate` to aggregate, graph ALL data |

## GA3 JOBs tasks

The are two tasks that execute GA3 recipes in JOBs.

![Ga3 Processing section](images/GA3%20Processing%20section.png)

| Task | When to use it |
| ---- | -------------- |
|<img src="images/ga3.svg" width="100">| **During acquisition**, for decision-making during the experiment. |
|<img src="images/ga3_after_run.svg" width="100">| **After acquisition**, for greater analysis flexibility when all the data are safely stored on the disk. |

## JOBs storage model

### Database (default)

By default all data are stored into the database, when multiple ND2 files have to be created they are linked through the database and appear as
a single dataset in the JOBS Explorer and JOBS Results.

<img src="images/Analysis database.png" width="400">

The GA3 recipe can produce any kind of tables and results (graphs, visualization, object catalogs). Some GA3 tables can be mapped into the JOBS Results Frame, Object and Tracking tables if they contain specific columns. If not the tables are displayed in a separate pane under the ND2 document.

In the `General Analysis 3` task GUI select where to store each table:

- **Auto** prefers JOBS Result tables and shows in parenthesis if possible
- **JOBS table** will store the GA3 table into JOBS Results
- **Custom GA3** will store the GA3 table into separate table

<img src="images/Save outputs.png" width="800">

#### JOBS Frames

The columns from the table appear in a group under the GA3 task name.

<img src="images/Database JOBS Frames.png" width="800">

#### Custom GA3

The columns are not in the table. Instead a button "Show Custom Results" appears.

<img src="images/Database Custom GA3.png" width="800">

The custom table is shown in the pane under the ND2 document.


<img src="images/Database Custom GA3 Results.png" width="800">

### Alternative Storage

When `Alternative Storage Location` task is in a JOB it bypasses the database altogether. ND2 files are stored into the specified folder. When a
GA3 task produces any results or table data it is stored as H5 sidecar files alongside the ND2s (in one-to-one fashion).

<img src="images/Alternative storage location.png" width="800">

The results are shown with the ND2 when it is opened.

<img src="images/Graf - After aquisition.png" width="800">

## The HDF5Concatenate node

The [HDF5Concatenate](https://nis-express-help.laboratory-imaging.com/ref/nodes/input-output/#czlimga3noderesultsloadandconcatenate) node, which is typically used to accumulate results across multiple files.

> Loads a result table from an HDF5 file specified either by the Filename parameter or by the latest HDF5 file in the current folder. It then appends records from the node’s input table. The table location within the HDF5 file is determined by the current analysis name and the node’s output name.

When the GA3 recipe contains a this node the relevant table contains all the records form previous and current H5. The last H5 file contains
complete set of records and results connected to that table. NIS-Elements opens automatically the last H5 if it finds such concatenation (the
H5 files contain links to previous and next H5).

The table below shows when it is suitable to use `HDF5Concatenate` node in the recipe.

|          |Database|Alternative storage|
|:-------- |:------:|:-----------------:|
|During run|NO      |NO                 |
|After run |YES      |YES                |

## Examples

### Example 1

Let's say we need to capture images at 7 different Z positions, and at each position we need to capture a time lapse consisting of 5 images. We prepare a JOB where we define a `Z-STACK LOOP` with 7 steps and a `TIME LOOP` with 5 captures in each Z-STACK iteration.

<img src="images/JOB definition.png" width="600">

Now we need to perform analysis on these images, so we prepare a GA3 recipe as shown below.

<img src="images/GA3 Recipe without HDF5Concatenate.png" width="400">

The last thing we need to do is define when the analysis will be applied to the captured images. As described above, we have two possibilities. For the first example, we choose to perform the analysis during the acquisition run (in reality, this depends on the current use case). For this reason, we use the `General Analysis 3` task. We want to save the results to the database, so we must disable the `Alternative Storage Location` task. The current JOB will look like this.

<img src="images/Current JOB definition 1.png" width="600">

After the JOB is done, the data will be saved in the database and we can access them by clicking on the analysis in the `JOBS Explorer`. Because the data is stored in the database, we do not need the `HDF5Concatenate` node in the recipe.

### Example 2

In the second example, we will consider the same JOB, but with a few differences. First, we do not need to perform the analysis during image acquisition. We can capture the images first and then perform the analysis separately. The second difference is that we want to save the results to an alternative storage location.

For this, it is necessary to activate the `Alternative Storage Location` task and the `Execute GA3 After Run` task, and to deactivate `General Analysis 3`. The current JOB looks like the image below.

<img src="images/Current JOB definition 2.png" width="600">

In this case, we need to modify the recipe because the data will be saved in separate HDF5 files. Since we want the data to be stored in one HDF5 file, it is necessary to add the `HDF5Concatenate` node to the recipe.

<img src="images/GA3 Recipe with HDF5Concatenate.png" width="400">

After the JOB is done, we can find the data in the HDF5 file in the location that we set in the `Alternative Storage Location` task.
