# Rare events - metaphase

In this example, the imaging phase is run over multiple locations at a
low rate. When a dividing cell is detected, it is automatically switched
to high-speed imaging.

Source image (red is cranked up using LUTs to see the round shape).

![Source image](images/ga3_rare_events_metaphase_example_01.png)

## 1. GA3 recipe

![Cells in metaphase](images/ga3_rare_events_metaphase_example_02.png)

To detect cells in metaphase using GA3, the following criteria are taken into account:
- Cells are small, round and well defined (threshold with restrictions on object size and circularity),
- nuclei are intense and well defined too (spot detection) and
- dividing cells have two nuclei.

All these criteria make up the following GA3 recipe:

![GA3 analysis definition](images/ga3_rare_events_metaphase_example_03.png)

![Bright Spots node](images/ga3_rare_events_metaphase_example_05.png)

![Threshold node](images/ga3_rare_events_metaphase_example_04.png)

![Aggregate Children node](images/ga3_rare_events_metaphase_example_06.png)

![Filter Records node](images/ga3_rare_events_metaphase_example_07.png)

![Filtering results](images/ga3_rare_events_metaphase_example_08.png)

![Detected metaphases](images/ga3_rare_events_metaphase_example_09.png)

![Detection on a different sample](images/ga3_rare_events_metaphase_example_10.png)

![Detection on a different sample](images/ga3_rare_events_metaphase_example_11.png)

## 2. GA3 in JOBS

Inside JOBs a regular pattern of points on a slide is analyzed every 30
minutes using a low magnification objective (“LoMag”). Every image is
analyzed by the GA3 defined above.The detected cells are then visited
and acquired with a high magnification objective (“HiMag”) every minute
for half an hour. If no dividing cell is found or after the high
magnification acquisition is finished, the experiment goes back to the
slow pace.

![JOBs definition](images/ga3_rare_events_metaphase_example_12.png)
