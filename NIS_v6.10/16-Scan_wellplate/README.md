# Scan Wellplate from Sample Navigation

To setup the Nikon Ti2 microscope for wellplate scanning from Sample Navigation see this [guide](https://github.com/Laboratory-Imaging/documents/blob/main/Ti2_Wellplate_Apps/system_setup_overview_objective.md).

![Service Settings](images/service_settings_window.png)

## Sample Navigation

To scan a well plate from Sample Navigation, first navigate to **View → Acquisition Controls → Sample Navigation**. Here, select the *Well Plate* tab.

![SN Window Default](images/sn_window_default.png)

#### 1. Detect plate

Next, detect the plate type and position using the "*Detect*" button:

![SN Window Detect](images/sn_window_detect.png)

#### 2. Define or import labeling and dosing

Then you can define the labeling and dosing of the wells using the "*Label Wells*" button:

![SN Window Label](images/sn_window_label.png)

#### 3. Run overview of the wells and create a well selection

Run the overwiew of the whole well plate using the "*Overview*" button and create a well selection using the "*Select Wells*" button.
 
![SN Window Overview and Select](images/sn_window_overview_select.png)

#### 4. Scan the wellplate

Finally, click the "*Scan*" button. A dialog window will open allowing the selection of the JOB to be used for scanning the well selection. Either a built-in job or a user-defined custom job can be used for the scan.

![SN Window Scan Dialog](images/sn_window_scan_dialog.png)

The scanning routine uses the current experiment settings.


Refer to the following examples for a concise description of the built-in jobs:
- [Brightfield Autofocus Scan](BFScanREADME.md)
- [Fluorescence Autofocus Scan](FluoScanREADME.md)


> [!NOTE]
> The *Custom Job* option allows the selection of any JOB saved in the currently selected project in the JOBS Explorer.

> [!TIP]
> If a JOB .bin file is stored in either Platform/[user.name]/ScanJob or Platform/ScanJob, the JOB is executed immediately when the "*Scan*" button is pressed. The path containing the [user.name] subfolder takes priority.