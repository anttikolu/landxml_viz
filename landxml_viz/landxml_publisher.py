"""Publish a LandXML / Inframodel model as a visualization_msgs/MarkerArray.

Precision note: RViz renders in float32, which only resolves ~0.5 m at GK24
magnitudes (~2.4e7). Vertices are therefore published relative to a local
origin that is stored in the (float64) marker pose, and the RViz fixed frame
should be a local frame (e.g. ``world``), not ``gk24`` itself.
"""

import math
import os

import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray

from landxml_viz.landxml_parser import parse_landxml, to_xyz


def _color(rgba):
    return ColorRGBA(r=float(rgba[0]), g=float(rgba[1]), b=float(rgba[2]), a=float(rgba[3]))


def _height_color(z, zmin, zmax, alpha):
    """Blue (low) -> green -> red (high)."""
    t = 0.5 if zmax - zmin < 1e-6 else (z - zmin) / (zmax - zmin)
    r = min(1.0, max(0.0, 2.0 * t - 0.5))
    b = min(1.0, max(0.0, 1.5 - 2.0 * t))
    g = 1.0 - abs(2.0 * t - 1.0) * 0.6
    return ColorRGBA(r=r, g=g, b=b, a=alpha)


class LandXmlPublisher(Node):

    def __init__(self):
        super().__init__('landxml_publisher')
        p = self.declare_parameter
        p('file_path', '')
        p('frame_id', 'gk24')
        p('topic', '/landxml/markers')
        p('swap_xy', True)               # LandXML is N,E,Z -> x=E, y=N
        p('strip_zone_prefix', False)    # gk24 in this system keeps the "24" prefix
        p('z_offset', 0.0)
        p('origin_mode', 'auto')         # 'auto' (rounded centroid) or 'manual'
        p('origin', [0.0, 0.0, 0.0])     # used when origin_mode == 'manual' (target-frame x,y,z)
        p('publish_period', 1.0)         # seconds; <= 0 publishes once (latched)
        p('show_surface', True)
        p('show_edges', True)
        p('show_breaklines', True)
        p('show_label', True)
        p('color_by_height', True)
        p('surface_color', [0.85, 0.55, 0.2, 0.6])
        p('edge_color', [0.1, 0.1, 0.1, 0.9])
        p('breakline_color', [1.0, 1.0, 0.0, 1.0])
        p('edge_width', 0.03)
        p('breakline_width', 0.06)

        self.markers = self._build_markers()

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.pub = self.create_publisher(MarkerArray, self._param('topic'), qos)
        self.pub.publish(self.markers)
        period = self._param('publish_period')
        if period > 0.0:
            self.create_timer(period, lambda: self.pub.publish(self.markers))

    def _param(self, name):
        return self.get_parameter(name).value

    def _build_markers(self) -> MarkerArray:
        path = os.path.expanduser(self._param('file_path'))
        if not path or not os.path.isfile(path):
            raise RuntimeError(f'file_path "{path}" does not exist')
        model = parse_landxml(path)

        swap, strip = self._param('swap_xy'), self._param('strip_zone_prefix')
        dz = self._param('z_offset')

        def xyz(pt):
            x, y, z = to_xyz(pt, swap, strip)
            return (x, y, z + dz)

        surfaces = []
        all_pts = []
        for s in model.surfaces:
            pts = {k: xyz(v) for k, v in s.points.items()}
            bls = [[xyz(q) for q in bl] for bl in s.breaklines]
            surfaces.append((s, pts, bls))
            all_pts.extend(pts.values())
            for bl in bls:
                all_pts.extend(bl)
        polylines = [(name, [xyz(q) for q in pl]) for name, pl in model.polylines]
        for _, pl in polylines:
            all_pts.extend(pl)
        if not all_pts:
            raise RuntimeError(f'No geometry found in {path}')

        if self._param('origin_mode') == 'manual':
            origin = tuple(float(v) for v in self._param('origin'))
        else:
            n = len(all_pts)
            origin = tuple(float(round(sum(p[i] for p in all_pts) / n)) for i in range(3))
        ox, oy, oz = origin

        def local(pt):
            return Point(x=pt[0] - ox, y=pt[1] - oy, z=pt[2] - oz)

        frame = self._param('frame_id')
        arr = MarkerArray()
        clear = Marker()
        clear.action = Marker.DELETEALL
        arr.markers.append(clear)

        def new_marker(ns, mid, mtype):
            m = Marker()
            m.header.frame_id = frame
            # stamp 0 -> RViz uses the latest available transform (works with bags / sim time)
            m.ns, m.id, m.type, m.action = ns, mid, mtype, Marker.ADD
            m.pose.position.x, m.pose.position.y, m.pose.position.z = ox, oy, oz
            m.pose.orientation.w = 1.0
            m.scale.x = m.scale.y = m.scale.z = 1.0
            m.frame_locked = True
            return m

        n_faces = n_bl = 0
        for si, (s, pts, bls) in enumerate(surfaces):
            zs = [p[2] for p in pts.values()] or [0.0]
            zmin, zmax = min(zs), max(zs)

            if self._param('show_surface') and s.faces:
                m = new_marker('surface', si, Marker.TRIANGLE_LIST)
                alpha = float(self._param('surface_color')[3])
                m.color = _color(self._param('surface_color'))
                for ids in s.faces:
                    tri = [pts[i] for i in ids]
                    # Make winding counter-clockwise seen from above so normals point up.
                    (x0, y0, _), (x1, y1, _), (x2, y2, _) = tri
                    if (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0) < 0:
                        tri = [tri[0], tri[2], tri[1]]
                    for v in tri:
                        m.points.append(local(v))
                        if self._param('color_by_height'):
                            m.colors.append(_height_color(v[2], zmin, zmax, alpha))
                arr.markers.append(m)
                n_faces += len(s.faces)

            if self._param('show_edges') and s.faces:
                m = new_marker('edges', si, Marker.LINE_LIST)
                m.scale.x = float(self._param('edge_width'))
                m.color = _color(self._param('edge_color'))
                seen = set()
                for ids in s.faces:
                    tri = [pts[i] for i in ids]
                    for a, b in ((0, 1), (1, 2), (2, 0)):
                        key = tuple(sorted((tuple(round(c, 3) for c in tri[a]),
                                            tuple(round(c, 3) for c in tri[b]))))
                        if key in seen:
                            continue
                        seen.add(key)
                        m.points.extend([local(tri[a]), local(tri[b])])
                arr.markers.append(m)

            if self._param('show_breaklines'):
                for bi, bl in enumerate(bls):
                    m = new_marker(f'breaklines_{si}', bi, Marker.LINE_STRIP)
                    m.scale.x = float(self._param('breakline_width'))
                    m.color = _color(self._param('breakline_color'))
                    m.points = [local(q) for q in bl]
                    arr.markers.append(m)
                n_bl += len(bls)

            if self._param('show_label') and pts:
                m = new_marker('label', si, Marker.TEXT_VIEW_FACING)
                cx = sum(p[0] for p in pts.values()) / len(pts)
                cy = sum(p[1] for p in pts.values()) / len(pts)
                m.pose.position.x, m.pose.position.y, m.pose.position.z = cx, cy, zmax + 2.0
                m.scale.z = 1.0
                m.color = _color([1.0, 1.0, 1.0, 1.0])
                m.text = s.name
                arr.markers.append(m)

        if self._param('show_breaklines'):
            for pi, (_, pl) in enumerate(polylines):
                m = new_marker('plan_features', pi, Marker.LINE_STRIP)
                m.scale.x = float(self._param('breakline_width'))
                m.color = _color(self._param('breakline_color'))
                m.points = [local(q) for q in pl]
                arr.markers.append(m)

        self.get_logger().info(
            f'Loaded {os.path.basename(path)}: {len(surfaces)} surface(s), {n_faces} faces, '
            f'{n_bl} breaklines, {len(polylines)} plan features. frame_id={frame}, '
            f'local origin=({ox:.3f}, {oy:.3f}, {oz:.3f})')
        if not math.isfinite(ox + oy + oz):
            raise RuntimeError('Non-finite origin')
        return arr


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LandXmlPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
