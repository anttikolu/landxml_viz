"""Namespace-agnostic LandXML / Inframodel parser (no ROS dependencies).

LandXML stores coordinates as "northing easting elevation". The parser returns
them unchanged; axis swapping is done by the caller (see ``to_xyz``).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

Point3 = Tuple[float, float, float]


@dataclass
class Surface:
    name: str
    points: Dict[str, Point3] = field(default_factory=dict)        # id -> (N, E, Z)
    faces: List[Tuple[str, str, str]] = field(default_factory=list)  # visible faces only
    breaklines: List[List[Point3]] = field(default_factory=list)


@dataclass
class LandXmlModel:
    surfaces: List[Surface] = field(default_factory=list)
    polylines: List[Tuple[str, List[Point3]]] = field(default_factory=list)  # PlanFeatures


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def _children(elem, name):
    return [c for c in elem if _local(c.tag) == name]


def _iter(elem, name):
    return (e for e in elem.iter() if _local(e.tag) == name)


def _parse_pnt_list(text: str) -> List[Point3]:
    vals = [float(v) for v in (text or '').split()]
    if len(vals) % 3:
        raise ValueError(f'PntList3D has {len(vals)} values, not a multiple of 3')
    return [tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)]


def parse_landxml(path: str) -> LandXmlModel:
    root = ET.parse(path).getroot()
    model = LandXmlModel()

    for surf_el in _iter(root, 'Surface'):
        surf = Surface(name=surf_el.get('name', ''))
        for defn in _children(surf_el, 'Definition'):
            for pnts in _children(defn, 'Pnts'):
                for p in _children(pnts, 'P'):
                    vals = [float(v) for v in p.text.split()]
                    surf.points[p.get('id')] = (vals[0], vals[1], vals[2] if len(vals) > 2 else 0.0)
            for faces in _children(defn, 'Faces'):
                for f in _children(faces, 'F'):
                    if f.get('i') == '1':  # invisible face
                        continue
                    ids = f.text.split()
                    if len(ids) == 3:
                        surf.faces.append((ids[0], ids[1], ids[2]))
        for bl in _iter(surf_el, 'Breakline'):
            for pl in _children(bl, 'PntList3D'):
                pts = _parse_pnt_list(pl.text)
                if len(pts) >= 2:
                    surf.breaklines.append(pts)
        missing = {i for f in surf.faces for i in f} - surf.points.keys()
        if missing:
            raise ValueError(f'Surface "{surf.name}" references unknown point ids: {sorted(missing)[:10]}')
        model.surfaces.append(surf)

    for pf in _iter(root, 'PlanFeature'):
        for pl in _iter(pf, 'PntList3D'):
            pts = _parse_pnt_list(pl.text)
            if len(pts) >= 2:
                model.polylines.append((pf.get('name', ''), pts))

    return model


def to_xyz(p: Point3, swap_xy: bool = True, strip_zone_prefix: bool = False) -> Point3:
    """Convert a LandXML (N, E, Z) point to (x, y, z) in the target frame."""
    n, e, z = p
    if strip_zone_prefix:
        e = e % 1_000_000.0  # e.g. 24480948 -> 480948
    return (e, n, z) if swap_xy else (n, e, z)
