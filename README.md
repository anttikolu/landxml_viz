# landxml_viz

ROS 2 package that reads a LandXML / Inframodel (4.x) file and publishes its TIN
surfaces, breaklines and plan features as a `visualization_msgs/MarkerArray` for
viewing in RViz2.

LandXML coordinates (northing, easting, elevation) are converted to the target frame
(default `gk24`: x = easting incl. zone prefix, y = northing, z = elevation).
Vertices are published relative to a local origin stored in the marker pose to avoid
float32 precision loss in RViz.

## Requirements

- ROS 2 Jazzy
- Python 3 (standard library only, no extra pip packages)
- ROS packages: `rclpy`, `visualization_msgs`, `geometry_msgs`, `std_msgs`,
  `launch`, `launch_ros`, `rviz2`
- A TF tree containing the target frame (`gk24`) and a local frame (e.g. `world`)
  to use as the RViz fixed frame

## Installation

```bash
cd ~/ros2_ws/src
git clone git@github.com:anttikolu/landxml_viz.git
cd ~/ros2_ws
rosdep install --from-paths src/landxml_viz --ignore-src -y
colcon build --packages-select landxml_viz
source install/setup.bash
```

Model files in `landxmlmodels/` (`*.xml`) are installed to
`share/landxml_viz/landxmlmodels`. Rebuild after adding or changing a model.

Run tests:

```bash
colcon test --packages-select landxml_viz && colcon test-result --verbose
```

## Running

Launch file (publisher + RViz2):

```bash
ros2 launch landxml_viz landxml_viz.launch.py
```

Node only:

```bash
ros2 run landxml_viz landxml_publisher --ros-args -p file_path:=/path/to/model.xml
```

### Launch file: `landxml_viz.launch.py`

| Argument       | Default                                                   | Description                           |
|----------------|-----------------------------------------------------------|---------------------------------------|
| `file_path`    | `share/landxml_viz/landxmlmodels/Puskunrata_Oja_...-0.200.xml` | LandXML file to publish          |
| `frame_id`     | `gk24`                                                    | Frame of the published markers        |
| `rviz`         | `true`                                                    | Start RViz2 with `rviz/landxml_viz.rviz` |
| `use_sim_time` | `false`                                                   | Use `/clock` (e.g. with rosbag playback) |

The RViz config uses `world` as fixed frame. Do not use `gk24` as the fixed frame;
GK24 coordinates are too large for RViz's float32 rendering.

## Node: `landxml_publisher`

### Subscribed topics

None.

### Published topics

| Topic              | Type                              | QoS                                   |
|--------------------|-----------------------------------|---------------------------------------|
| `/landxml/markers` | `visualization_msgs/MarkerArray`  | reliable, transient local, depth 1    |

Marker namespaces: `surface` (TRIANGLE_LIST), `edges` (LINE_LIST),
`breaklines_<n>` (LINE_STRIP), `plan_features` (LINE_STRIP), `label` (TEXT_VIEW_FACING).
In RViz, set the MarkerArray display durability to *Transient Local*.

### Parameters

| Name                | Type     | Default                   | Description |
|---------------------|----------|---------------------------|-------------|
| `file_path`         | string   | `""`                      | LandXML file to load (required) |
| `frame_id`          | string   | `gk24`                    | `header.frame_id` of the markers |
| `topic`             | string   | `/landxml/markers`        | Output topic |
| `swap_xy`           | bool     | `true`                    | Map LandXML N,E,Z to x=E, y=N |
| `strip_zone_prefix` | bool     | `false`                   | Remove GK zone prefix from easting (24480948 → 480948) |
| `z_offset`          | double   | `0.0`                     | Added to all elevations [m] |
| `origin_mode`       | string   | `auto`                    | `auto` = rounded centroid, `manual` = use `origin` |
| `origin`            | double[] | `[0.0, 0.0, 0.0]`         | Local origin in target frame (when `manual`) |
| `publish_period`    | double   | `1.0`                     | Republish period [s]; `<= 0` publishes once |
| `show_surface`      | bool     | `true`                    | Publish TIN surface |
| `show_edges`        | bool     | `true`                    | Publish triangle edges |
| `show_breaklines`   | bool     | `true`                    | Publish breaklines and plan features |
| `show_label`        | bool     | `true`                    | Publish surface name text |
| `color_by_height`   | bool     | `true`                    | Colour surface by elevation (blue low → red high) |
| `surface_color`     | double[] | `[0.85, 0.55, 0.2, 0.6]`  | RGBA; alpha also used with `color_by_height` |
| `edge_color`        | double[] | `[0.1, 0.1, 0.1, 0.9]`    | RGBA |
| `breakline_color`   | double[] | `[1.0, 1.0, 0.0, 1.0]`    | RGBA |
| `edge_width`        | double   | `0.03`                    | Edge line width [m] |
| `breakline_width`   | double   | `0.06`                    | Breakline width [m] |
