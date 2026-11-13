import os

import pytest

from landxml_viz.landxml_parser import parse_landxml, to_xyz

TRENCH = os.path.expanduser(
    '~/Puskunrata_Oja_keskella_pohja_160cm_luiskat_1_2_100_45_100_75-0.200.xml')

MINIMAL = """<?xml version="1.0" encoding="ISO-8859-1"?>
<LandXML xmlns="http://buildingsmart.fi/inframodel/404" version="1.2">
 <Surfaces><Surface name="s">
  <SourceData><Breaklines><Breakline>
   <PntList3D>10 20 1 11 21 2</PntList3D>
  </Breakline></Breaklines></SourceData>
  <Definition surfType="TIN">
   <Pnts><P id="1">0 0 0</P><P id="2">0 1 0</P><P id="3">1 0 1</P></Pnts>
   <Faces><F>1 2 3</F><F i="1">1 2 3</F></Faces>
  </Definition>
 </Surface></Surfaces>
</LandXML>
"""


def test_minimal(tmp_path):
    f = tmp_path / 'm.xml'
    f.write_text(MINIMAL, encoding='iso-8859-1')
    m = parse_landxml(str(f))
    s = m.surfaces[0]
    assert len(s.points) == 3
    assert s.faces == [('1', '2', '3')]  # invisible face skipped
    assert s.breaklines == [[(10.0, 20.0, 1.0), (11.0, 21.0, 2.0)]]


def test_to_xyz():
    p = (6815309.2, 24481011.5, 100.5)
    assert to_xyz(p) == (24481011.5, 6815309.2, 100.5)
    assert to_xyz(p, strip_zone_prefix=True)[0] == pytest.approx(481011.5)


@pytest.mark.skipif(not os.path.isfile(TRENCH), reason='trench file not present')
def test_trench_file():
    m = parse_landxml(TRENCH)
    assert len(m.surfaces) == 1
    s = m.surfaces[0]
    assert len(s.points) == 60
    assert len(s.faces) == 20
    assert len(s.breaklines) == 27
    xs, ys, zs = zip(*(to_xyz(p) for p in s.points.values()))
    assert 24480948 < min(xs) and max(xs) < 24481017
    assert 6815305 < min(ys) and max(ys) < 6815368
    assert min(zs) == pytest.approx(100.25) and max(zs) == pytest.approx(100.55)
