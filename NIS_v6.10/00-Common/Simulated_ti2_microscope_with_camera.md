# Simulated Nikon Ti2 with camera simulator

## 1. Device manager setup

Following window is found in `Devices -> Devices Manager`.

- Nikon Ti2 Simulator
- Simulator
- DIA Lamp
- D-LEDI Simulator

![Device manager](images/dm_ti2_microscope_with_camera.png)

In Device manager select the camera "Simulator File". Then select "mono camera":

![Select camera in device manager](images/dm_add_camera.png)

Add EPI light source:

Right-click on the upper lapp and select "Configure..."

![Configure upper LAPP](images/dm_ti2_microscope_lapp_upper.png)

Add the EPI by dragging it from the list on the left to the top position.

![LAPP EPI](images/dm_ti2_microscope_lapp_epi.png)

![Select EPI light in device manager](images/dm_add_dledi.png)

## 2. Camera setup

You can now close Device manager and open Acquisition window in `View -> Acquisition Controls -> Acquisition`.

Camera simulator plays a provided ND2 file in a loop.

![Camera simulator](images/camera_simulator_settings.png)

| :exclamation: Make sure to uncheck the "File metadata" to use the current microscope settings.|

Set some mono ND2 file and check the live (menu: Acquire -> Live Fast).

## 3. Microscope setup

Add objectives so that we have calibrated images.

![Nosepiece setup](images/Setup_nosepiece.png)

Add some filters into Turret 1:

![Filter setup](images/Setup_filters.png)

![Ti2 Microscope pad](images/Ti2_pad.png)

## 4. Objectives

Following window is found in `Calibration -> Objectives`.

Check that objectives are calibrated (the calibrations are taken form Hamamatsu simulator):

![Objective calibration](images/Objectives.png)

Each example will state what calibration and which objective was used when the example was made.

To set it, select the objective, run live and calibrate it as follows:

![Calibrate objective](images/Calibrate_live_1.png)

Select manual method:

![Calibrate objective](images/Calibrate_live_2.png)

Click on Set Pixel Size... and enter the number

![Calibrate objective](images/Calibrate_live_3.png)

## 5. Simulated Stage setup

Following window is found in `View -> Acquisition Controls -> XYZ Overview`.

Set the current stage position roughly in the middle of the scan area in order to avoid hitting the stage limits.
![XYZ Overview: go to the middle](images/xyz_overview.png)

Alternatively in `View -> Acquisition Controls -> XYZ Navigation`.

Set values for X, Y and Z directly: <br>
![xyz-navigation](images/xyz_navigation.png)
