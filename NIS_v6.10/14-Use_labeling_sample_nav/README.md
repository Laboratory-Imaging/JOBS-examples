# Use Labeling from Sample Navigation

In this example, we will demonstrate the functionality of tasks that can import well selection and well labeling from Sample Navigation.

## Setting up the JOB

First, we will drag in the `Use Autodetected Plate` task.

![Autodetected Plate Task](../14-Use_labeling_sample_nav/images/use_autodet_plate_task.png)

Next, we will import the selection of wells that are selected in Sample Navigation using the `Use Well Selection from Sample Navigation`. In our case, we selected these wells in Sample Navigation:

![SN Selection](../14-Use_labeling_sample_nav/images/sample_nav_selection2.png)

Import the selection using the task: 

![Import SN Selection Task](../14-Use_labeling_sample_nav/images/selection_sample_nav_task.png)

We will also label some of the wells in Sample Navigation with custom labels like so:

![SN Labeling](../14-Use_labeling_sample_nav/images/sample_nav_selection_labels2.png)

We can import the well labeling (and dosing, should it be defined) from Sample Navigation using the `Use Well Labeling from Sample Navigation` task:

![Import SN Labeling Task](../14-Use_labeling_sample_nav/images/labeling_sample_nav_task.png)

Finally, we will capture the well centers of the wells in the imported selection:

![Well Loop](../14-Use_labeling_sample_nav/images/well_loop.png)


After running the job, you can see that only the selected wells have been captured:

![Run Wells](../14-Use_labeling_sample_nav/images/run_images.png)

You can also see the imported labels after clicking the "Show Labeling" button:

![Run Labels](../14-Use_labeling_sample_nav/images/run_labels.png)


JOB file: <!---[[View on GitHub](14-UseDetectedPlateAndLabelingSampleNavigation.bin)]--> [[Download link](https://laboratory-imaging.github.io/JOBS-examples/NIS_v6.10/14-Use_labeling_sample_nav/14-UseDetectedPlateAndLabelingSampleNavigation.bin)] [[View as html](https://laboratory-imaging.github.io/JOBS-examples/NIS_v6.10/14-Use_labeling_sample_nav/14-UseDetectedPlateAndLabelingSampleNavigation.html)]



