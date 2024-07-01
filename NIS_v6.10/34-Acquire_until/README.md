# Acquire until a condition is met

The goal of this example is to run an experiment until a condition is met.

In the following examples we will use  the Number of cells or the Standard Error (SE) of the equivalent diameter feature as the termination condition. There are many other examples which use different condition. Acquire until:
- most of the cells are dead,
- cells are bleached,
- ...

> [!NOTE]
> This example is shown on simulated devices - it doesn't require any real hardware for trying it out.

## Contents
- [Hardware setup](#hardware-setup)
- [Acquire a time-lapse until a given number of cells is reached](#acquire-a-time-lapse-until-a-given-number-of-cells-is-reached)
- [Acquire a time-lapse until a given cell feature statistic is reached](#acquire-a-time-lapse-until-a-given-cell-feature-statistic-is-reached)
- [Stop acquiring wells that reached a given Standard Error (SE))](#stop-acquiring-wells-that-reached-a-given-standard-error-se)

## Hardware setup

[Setup a Nikon Ti2 Simulator](../00-Common/Simulated_ti2_microscope_with_camera.md)

### Camera File simulator setup

For camera simulator we will use an artificial two-frame time-lapse. The second frame is darker version of the first frame.

[synthetic-objects-timelapse.nd2](synthetic-objects-timelapse.nd2)

![sample movie: synthetic-objects-timelapse.nd2](images/01-synthetic-timelapse.png)

Open it in NIS Elements and set it into the camera simulator by clicking on "Load current ND" in the Camera Simulator settings.

![Camera simulator](../00-Common/images/camera_simulator_settings.png)

Then, setup the rest of the acquisition settings:
- select the D-LEDI, 
- check the correct file in the camera simulator,
- select the 60x lens and
- select the DAPI filter cube in the upper turret

![Acquisition settings](images/02-Acquisition_settings.png)

| :exclamation: set |  value         |
| ----------------  | -------------- |
| Calibration       | 0.18 µm/px     |
| Objective         | Plan Apo λ 60x |

## Acquire a time-lapse until a given number of cells is reached

Before starting with the GA3 we need a time-lapse to work with. Lets first create a job that will do that. We will later use it as a starting point. This way we are sure that we have the right material for the GA3 recipe.

### 1. Run simple time-lapse with the configuration

Create a simple JOB with only two tasks:
- TimeLoop with Unknown duration (meaning: infinite unless stopped) and
- Capture that uses current settings

![JOB: AcquireCells](images/10-AcquireCells_job.png)

Save the JOB and run it. Finish it manually (remember it has infinite duration), after couple of frames are acquired. Then, open the ND2 file by clicking on any row in the JOB results table.

![Acquired time-lapse](images/12-AcquireCells_image.png)

Final JOB: [0-AcquireCells.bin](0-AcquireCells.bin)

### 1. Create a GA3 recipe that counts the number of cells in an image

Now, that we have a time-lapse we can work on the GA3 recipe.

Create a new recipe (menu: Image -> New GA3 recipe...) and
add following nodes:
- Threshold from the Segmentation tab and 
- ObjectCount from the Measurement tab.

Connect them as follows:

![GA3 recipe - CellCount](images/04-ga3_CellCount.png)

Now set the node parameters like in the screenshot:

![GA3 recipe - Parameters](images/05-ga3_node_settings.png)

The final GA3 recipe: [CellCount.ga3](CellCount.ga3)

The resulting Records:

![GA3 results](images/06-Records_1.png)

![GA3 results](images/07-Records_2.png)

We can see that one frame has 54 and the second has 48 cells.

Final GA3 recipe: [CellCount.ga3](CellCount.ga3)

### 2. Create the JOB that will stop after it acquires 1000 cells

Open the JOB that we created previous section. Start by saving the JOB under different name in order to preserve the original one.

Add the following tasks to it:
- Variables task at the beginning,
- GA3 task after the Capture task,
- Expression task after the GA3 task to accumulate the totalCellCount
- If task to check if the total count is met yet and
- Break task inside the If task block to end the loop.

![JOB: Acquire 1k cells](images/20-Acquire1kCells_job.png)

In the Variables task, add a new variable `totalCellCount` of type int. Check "always initialize" and set the initial value to 0.

![JOB: Variables task](images/25-Variables.png)

In the GA3 task:
- select the CellCount recipe (it should change the name of the task to CellCount too),
- in the "Save outputs" tab uncheck All under Images and 
- in the "Export parameters" tab check CellCount in the "Records" table.

Images below show the relevant tabs.

![JOB: GA3 task](images/21-ga3_task_1.png)

![JOB: GA3 task task](images/22-ga3_task_2.png)

In the Expression task we will accumulate the totalCellCount variable:

```c
totalCellCount = totalCellCount + Job.CellCount.Tables.Records.CellCount.First
```

Meaning literally: Take the number in `totalCellCount` (initially zero), add the cellCount coming from the GA3 to it and set it back to `totalCellCount` variable.

In order to understand the `Job.CellCount.Tables.Records.CellCount.First` term we can break it down into:
- `Job.CellCount` part which represents the GA3 task named CellCount in this Job,
- `Tables.Records.CellCount` part representing the column CellCount in the Records table and
- `First` part means - take only the first row from the table (we have only one row in the table anyway).

![JOB: Expression task](images/23-expression.png)

An If task needs an expression so that it can decide at runtime wether it should execute the tasks in the if block or not. The expression evaluates either to 
- *zero* meaning "no" or 
- *non zero* meaning "yes".

In our case we enter the following expression:

```c
totalCellCount >= 1000
```

Meaning: when the variable `totalCellCount` is greater or equal than 1000 (= "yes") execute the tasks inside the if block (that is *break*)  otherwise skip the block.

![JOB: If task](images/24-if_task.png)

When the break is executed it will break from the Time lapse loop and effectively end the JOB as there is nothing after the loop task.

We expect the JOB to acquire 20 frames as one frame has around 50 cells. Let's try it out and run the JOB. The results show that the acquisition actually stopped after 20 frames.

![JOB: results](images/26-Job_results.png)

Final JOB: [1-Acquire1kCells.bin](1-Acquire1kCells.bin)

## Acquire a time-lapse until a given cell feature statistic is reached

This example builds upon the previous one. But, instead of using the *count* of objects as a statistic for deciding when to stop, it will use slightly more complex one: [Standard Error (SE)](https://en.wikipedia.org/wiki/Standard_error). 

$SE = \Large\sqrt{\frac{\sigma^2}{N}}$ where $\sigma^2$ is *variance* and $N$ is the number of cells.

We will use the *equivalent diameter* as object feature.

> [!NOTE]
> From the NIS Elements help on EqDiameter feature: \
> It is a size feature derived from the object area. It is the diameter of a circle with the same area as the measured object. \
> $EqDiameter = \Large\sqrt{\frac{4*Area}{pi}}$

Since we need the SE to be calculated for all the frames so far we need a formula for adding two variances, the accumulated so far and the current one.

It turns out there is such a formula:

$\Large{n_T = n_l + n_c}$

$\Large{\mu_T = \frac{n_l*\mu_l + n_c*\mu_c}{N}}$

$\Large{\sigma_T = \frac{n_l*((\mu_l - \mu_T)^2 + \sigma_l) + n_c*((\mu_c - \mu_T)^2 + \sigma_c)}{n_T}}$

where:
- $n_T$, $n_l$ and $n_c$ is total, last and current count
- $\mu_T$, $\mu_l$ and $\mu_c$ is total, last and current mean
- $\sigma_T$, $\sigma_l$ and $\sigma_c$ is total, last and current variance

We made a convenience macro function to perform this calculation:
```c
int UpdateMeanAndVariance(int* totalN, double* totalMean, double* totalVar, int n, double mean, double* var);
```

Now that we have figured out the statistics, we will reuse the GA3 from the previous example and slightly update it. We need to output three statistics: CellCount (the $n_c$), MeanEqDia (the $\mu_c$) and VarEqDia (the $\sigma_c$). Actually only two, because CellCount we already have. As these statistics are all per frame, we will just add two new columns in the same ObjectCount node:

![GA3 recipe: object count node](images/33-GA3_ObjectCount.png)

The final GA3 recipe: [CellCountMeanVar.ga3](CellCountMeanVar.ga3)

In the JOB we will "accumulate" not only the totalCellCount but the totalMean and totalVariance too. As we saw earlier the formulae are quite complex and we have the convenience function that will do it all. Then, we have to:
- create convenience variables n, mean and var to shorten the code,
- update the totalCellCount, totalMean and totalVar variables using the UpdateMeanAndVariance function and
- calculate the SE according to the above SE formula.

```c
int n = Job.CellCount.Tables.Records.CellCount.First;
double mean = Job.CellCount.Tables.Records.MeanEqDia.First;
double var = Job.CellCount.Tables.Records.VarEqDia.First;
UpdateMeanAndVariance(&totalCellCount, &totalMean, &totalVar, n, mean, var);

if (totalCellCount > 0)
{
    SE = sqrt(totalVar/totalCellCount);
}
```

We will modify the JOB from the previous example as follows:
- in Variables task create three new variables totalMean, totalVar and SE,
- in GA3 task add two more columns MeanEqDia and VarEqDia,
- exchange the Expression task for a Macro task and insert the code from above and 
- in the If task change the expression to evaluate the SE.

![JOB](images/30-AcquireToGivenEqDiaSE_job.png)

![JOB](images/31-ga3_task_1.png)

We want the experiment to stop when the SE drops below 0.1.

![JOB](images/32-if_task.png)

Final JOB: [2-AcquireToGivenEqDiaSE.bin](2-AcquireToGivenEqDiaSE.bin)

When we run the JOB we see it has 8 frames and that it needed 408 objects to get the SE to 0.099.

![GA3: check SE results](images/38-GA3_CheckSE_results.png)

The GA3 for calculating the SE of all Object EqDiameter is straightforward:
- connect the Object Measurement node to binaries and add EqDiameter feature,
- append Accumulate node over time and 
- append Reduce node and select StdErr.

![GA3: recipe](images/37-GA3_CheckSE.png)

The GA3 recipe to check the result: [CheckSE.ga3](CheckSE.ga3)

## Stop acquiring wells that reached a given Standard Error (SE)

We will further extend the previous example to a well-plate and calculate the SE (and the relevant statistics) for every well. 
In the well loop we will check the calculated SE in every well and skip it if the SE is below the given threshold.
The well loop itself is in the time loop that is already in the JOB.
We have to keep track of the visited wells and stop (break from the time loop) when we are skipping all wells.

We reuse the GA3 recipe from the previous example without any change.

In the JOB we have to make some changes though. 
Lets start with the Variables task where we change all variables to arrays (of 96 elements) and add one more:
- totalCounts, totalMeans, totalVars, SEs: all defined as array of 96 doubles.
- wellsVisited: defined as double scalar value

![JOB Variables](images/41-Variables.png)

Then we modify the rest of the JOB as follows:
- Plate definition task goes below the Variables task,
- insert the Well selection below it and select two wells only,
- the Well loop task goes inside the time loop,
- before the well loop (inside the time loop) add Expression task and set the variable wellsVisited to 0 in it
- after the well loop add the If task and check the number of wellsVisited equals to zero and
- in the If task insert the Break task.

The Macro has to change a bit too:

- All the `totalCounts[i]`, `totalMeans[i]`, `totalVars[i]` and `SEs[i]` must have an index (they are arrays),
- The index `int i = Job.Wells.Current` refers to current well.
- Finally we update `wellsVisited` variable.

```c
int i = Job.Wells.Current;
int n = Job.CellCountMeanVar.Tables.Records.CellCount.First;
double mean = Job.CellCountMeanVar.Tables.Records.MeanEqDia.First;
double var = Job.CellCountMeanVar.Tables.Records.VarEqDia.First;
UpdateMeanAndVariance(totalCounts + i, totalMeans + i, totalVars + i, n, mean, var);
if (totalCounts[i] > 0)
{
    SEs[i] = sqrt(totalVars[i]/totalCounts[i]);
}
wellsVisited = wellsVisited + 1;
```

> [!Note]
> Currently, the NIS Elements macro has a syntax limitation. Following code is perfectly valid in c but it will not work in the NIS Elements macro:\
> `UpdateMeanAndVariance(&totalCounts[i], &totalMeans[i], &totalVars[i], n, mean, var);` \
> To make it work use the pointer syntax instead:\
> `UpdateMeanAndVariance(totalCounts + i, totalMeans + i, totalVars + i, n, mean, var);`

![JOB](images/40-AcquireWellToGivenEqDiaSE_job.png)

After we run the example we get the results and can check the SE per well:

![JOB results](images/45-Job_results.png)

Final JOB: [3-AcquireWellToGivenEqDiaSE.](3-AcquireWellToGivenEqDiaSE.bin)

To get below SE < 0.1 it took 8 and 9 frames for the two wells and 384 and 480 objects respectively.
This is because the simulator has two frames - one with more wells than the other - and as we acquired only two wells one had constantly more objects for every capture than the other.

![GA3 Check well SE results](images/46-GA3_CheckWellSE_results.png)

The GA3 for checking the SE had to be slightly modified:
- AccumRecords should be over *all* loops (Time and Well loop) and
- Reduce node should group over multi-point index in order to reduce over it. 

![GA3: recipe](images/47-GA3_CheckWellSE.png)

The GA3 recipe to check the result: [CheckWellSE.ga3](CheckWellSE.ga3)
