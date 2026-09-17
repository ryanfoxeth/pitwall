"""Check geographic mesh coverage, face direction and normalization before export."""
import json
import math
from pathlib import Path

p = json.loads((Path(__file__).resolve().parents[1] / 'Assets/Monaco/MonacoGeography.json').read_text())
def area(points):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])) / 2

for group in ('waterTriangles', 'terrain'):
    assert all(area(t) > 0 for t in p[group]), f'{group}: reversed or degenerate faces'
    assert all(math.isfinite(v) for t in p[group] for point in t for v in point)
water_area = area(p['water'])
assert abs(sum(area(t) for t in p['waterTriangles']) - water_area) < 1, 'Harbor has holes or overlaps'
assert len(p['landmarks']) == 4 and len(p['buildings']) >= 40
span = max(max(v[i] for v in p['track']) - min(v[i] for v in p['track']) for i in (0, 1))
scale = .55 / span
extent = max(max(v[i] for v in p['boundary']) - min(v[i] for v in p['boundary']) for i in (0, 1)) * scale
assert .55 < extent < .70, f'Unexpected tabletop bounds: {extent}'
print(f'Monaco geometry passed: {len(p["terrain"])} terrain triangles, complete {water_area:.1f} m² harbor, {extent:.3f} m authored footprint')
