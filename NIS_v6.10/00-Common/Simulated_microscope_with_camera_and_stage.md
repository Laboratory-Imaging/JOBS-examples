# Simulated manual microscope with camera and stage sumilators

## 1. device manager setup
- Manual Microscope
- Simulator
- Manual light
- StageSim

![Device manager](images/dm_manual_microscope_with_camera_and_stage.png)

## 2. Camera setup

Camera simulator plays a provided ND2 file in a loop.

![Camera simulator](images/camera_simulator_settings.png)

## 3. Stage setup

Initiate the state (menu Devices -> Initiate Stage...).

> [!NOTE]
> With StageSim device this initiation must be done after every start of NIS Elements.

![Initiate stage](images/initiate_stage.png)

Set the current stage position roughly in the middle of the scan area in order to avoid hitting the stage limits.
![XYZ Overview: go to the middle](images/xyz_overview.png)