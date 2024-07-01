# Simulated Nikon Ti2 with camera simulator

## 1. device manager setup
- Nikon Ti2 Simulator
- Simulator 
- DIA Lamp
- D-LEDI Simulator

![Device manager](images/dm_ti2_microscope_with_camera.png)

In Device manager select the camera "Simulator File". Then select "mono camera":

![Select camera in device manager](images/dm_add_camera.png)

Add EPI light source:

![Select EPI light in device manager](images/dm_add_dledi.png)

## 2. Camera setup

Camera simulator plays a provided ND2 file in a loop.

![Camera simulator](images/camera_simulator_settings.png)

Set some mono ND2 file and check the live (menu: Acquire -> Live Fast).

## 3. Microscope setup

Add objectives so that we have calibrated images.

![Nosepiece setup](images/Setup_nosepiece.png)

Add some filters into Turret 1:

![Filter setup](images/Setup_filters.png)

![Ti2 Microscope pad](images/Ti2_pad.png)

## 4. Objectives

Check that objectives are calibrated (the calibrations are taken form Hamamtsu simulator):

![Objective calibration](images/Objectives.png)

Examples of reasonable calibrations by objective magnifications for 2k x 2k images:

| Magnification [x] | Calibration [µm] |
|-------------------|------------------|
| 2                 | 3.250            |
| 10                | 0.650            |
| 20                | 0.325            |
| 40                | 0.163            |
| 60                | 0.108            |
| 100               | 0.065            |

Each example will state what calibration and which objective was used when the example was made.

To set it, select the objective, run live and calibrate it as follows:
![Calibrate objective](images/Calibrate_live_1.png)

Select manual method:

![Calibrate objective](images/Calibrate_live_2.png)

Click on Set Pixel Size... and enter the number

![Calibrate objective](images/Calibrate_live_3.png)


## 5. Stage setup

Set the current stage position roughly in the middle of the scan area in order to avoid hitting the stage limits.
![XYZ Overview: go to the middle](images/xyz_overview.png)
