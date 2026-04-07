## Title: LILA Player Journey Visualization Architecture

## Overview
This tool is built to translate raw telemetry data (Parquet) into a visual, interactive dashboard for Level Designers. It focuses on temporal spatial analysis, allowing designers to see not just where a player ended up, but the exact pathing and decision-making process they took to get there.

## Technical Stack
Frontend/UI: Streamlit (for rapid dashboarding and state management).

Data Processing: Pandas & PyArrow (for high-performance Parquet ingestion).

Visualization: Plotly Graph Objects (to allow for layering coordinate data over static image assets).

## Coordinate Mapping Methodology
The most critical component of the architecture is the World-to-Pixel Transformation. Game engines use 3D Cartesian coordinates (X,Y,Z), while the minimaps are 2D static images.

The transformation follows this linear scaling formula:

We define the transformation from World Space $\mathbb{W}$ to Pixel Space $\mathbb{P}$ as follows:

$$
\begin{cases}
x_p = \frac{x_w - O_x}{s} \cdot 1024 \\
y_p = \left( 1 - \frac{z_w - O_z}{s} \right) \cdot 1024
\end{cases}
$$

**Where:**
* $(x_p, y_p) \in [0, 1024]^2$ are the resulting image coordinates.
* $(x_w, z_w)$ are the raw telemetry coordinates from the Parquet data.
* $(O_x, O_z)$ is the world-space origin point of the minimap.
* $s$ is the scalar value representing the world-units covered by the map. 

## World-to-Minimap Coordinate Conversion

To plot a world coordinate `(x, z)` onto the minimap image:

```
Step 1: Convert world coords to UV (0-1 range)
  u = (x - origin_x) / scale
  v = (z - origin_z) / scale

Step 2: Convert UV to pixel coords (1024x1024 image)
  pixel_x = u * 1024
  pixel_y = (1 - v) * 1024    ← Y is flipped (image origin is top-left)
```

**Example** (AmbroseValley, scale=900, origin=(-370, -473)):
```
World position: x=-301.45, z=-355.55

u = (-301.45 - (-370)) / 900 = 68.55 / 900 = 0.0762
v = (-355.55 - (-473)) / 900 = 117.45 / 900 = 0.1305

pixel_x = 0.0762 * 1024 = 78
pixel_y = (1 - 0.1305) * 1024 = 890
```

**Note:** The `y` column in the data represents **elevation/height** in the 3D world, not a 2D map coordinate. For 2D minimap plotting, use only `x` and `z`.


## Modules Used 
1. Streamlit: The UI Framework
Why: Speed of development and interactivity.

Role: It allowed you to turn a Python script into a full-fledged web application without needing a frontend engineer.

UX Context: It handles the "Session State" for your animation controls and provides the sidebar filters (sliders and selectboxes) that allow a Level Designer to interact with the data in real-time.

2. Pandas: The Data Manipulation Engine
Why: It is the industry standard for handling tabular data.

Role: Used for filtering thousands of rows of telemetry, grouping data by match_id, and calculating the "seconds elapsed" for your timeline.

UX Context: It allowed you to quickly pivot between "Macro" (all kills in a day) and "Micro" (one specific player's journey) views.

3. Plotly: The Interactive Visualization Layer
Why: Unlike static plotting libraries, Plotly allows for zooming, panning, and hovering.

Role: Used to layer the scatter plots (player paths) and contour plots (heatmaps) over the map image.

UX Context: Level Designers need to zoom into specific buildings or "loot rooms." Plotly’s built-in toolbar allows them to inspect micro-interactions without you having to write extra code.

4. PyArrow & FastParquet: The Performance Pair
Why: Parquet files are columnar and compressed; they are much faster to read than CSVs.

Role: These libraries act as the "engine" that allows Pandas to read the .parquet files provided in the LILA dataset.

UX Context: When dealing with 150+ match files, using pyarrow ensures the app doesn't hang or freeze while loading, providing a "snappy" user experience.

5. Pillow (PIL): The Image Processor
Why: Handling raw image data.

Role: Used to open and process the .png and .jpg minimap files.

UX Context: It ensures the background maps are loaded correctly and passed into Plotly with the correct dimensions, providing the spatial context for the player coordinates.