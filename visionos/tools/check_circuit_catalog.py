#!/usr/bin/env python3
"""Check the bundled calendar coverage and geometric assumptions used by RealityKit."""
import json
import math
from pathlib import Path
rows = json.loads((Path(__file__).resolve().parents[1] / 'Sources/Resources/Season2026.json').read_text())
assert len(rows) == 23
assert sum(bool(row.get("elevationSource")) for row in rows) == 22
assert len({row['id'] for row in rows}) == len(rows)
assert [row['round'] for row in rows] == list(range(1, 24))
upcoming = [row for row in rows if row['date'] >= '2026-09-17']
assert len(upcoming) == 9 and upcoming[0]['id'] == 'baku'
assert [row['id'] for row in upcoming] == ['baku', 'sepang', 'marina_bay', 'americas', 'rodriguez', 'interlagos', 'vegas', 'losail', 'yas_marina']
for row in rows:
    points = row['points']
    assert len(points) > 50, row['id']
    assert all(len(p) == 3 and all(math.isfinite(x) for x in p) for p in points), row['id']
    source = row.get('elevationSource')
    if source:
        assert source['survey_grade'] is False and 'not surveyed' in row['elevation']
        height = max(p[2] for p in points)-min(p[2] for p in points)
        assert 1 < height < 150
        if row['id'] == 'monaco':
            assert 40 < height < 43
        else:
            assert len(source['laps']) >= 3
            assert len({lap['driver_number'] for lap in source['laps']}) >= 2
            assert source['cross_lap_rms_m'] <= 5 and source['max_lap_spread_m'] <= 15
            assert all(lap['horizontal_fit_rms_m'] <= 40 for lap in source['laps'])
    else:
        assert all(p[2] == 0 for p in points) and 'Flat' in row['elevation'], row['id']
    assert max(math.dist(a, b) for a, b in zip(points, points[1:] + points[:1])) < 25.01, row['id']
    assert all(min(p[i] for p in points) < max(p[i] for p in points) for i in (0, 1)), row['id']
print('PASS: 23 circuits, 9 upcoming, finite closed geometry, <=25m segments, explicit elevation provenance')
