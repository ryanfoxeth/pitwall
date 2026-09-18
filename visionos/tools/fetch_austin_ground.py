"""Sample Austin's USGS 3DEP 1m ground model without downloading the full tile.
Usage: python fetch_austin_ground.py GROUND_DIRECTORY
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import from_bounds

folder = Path(sys.argv[1])
metadata_file = folder / 'americas-usgs-products.json'
if not metadata_file.exists():
    query = urllib.parse.urlencode({
        'datasets': 'Digital Elevation Model (DEM) 1 meter',
        'bbox': '-97.65,30.12,-97.62,30.15',
        'prodFormats': 'GeoTIFF', 'outputFormat': 'JSON', 'max': 20,
    })
    with urllib.request.urlopen('https://tnmaccess.nationalmap.gov/api/v1/products?' + query, timeout=45) as response:
        metadata_file.write_bytes(response.read())
products = json.loads(metadata_file.read_text())['items']
# Pin the sampled acquisition instead of trusting catalog ordering.
product = next(p for p in products if p['downloadURL'].endswith('USGS_one_meter_x63y334_TX_Central_B1_2017.tif'))
url = product['downloadURL']
data = json.loads((folder / 'americas.json').read_text())
projection, grid = data['projection'], data['grid']
shape = np.asarray(grid['heights']).shape
xx, yy = np.meshgrid(grid['x0'] + np.arange(shape[1]) * grid['step'], grid['y0'] + np.arange(shape[0]) * grid['step'])
land_lonlat = np.stack([xx, yy], -1) / projection['factors'] + projection['origin']
catalog = json.loads((Path(__file__).resolve().parents[1] / 'Sources/Resources/Season2026.json').read_text())
circuit = next(c for c in catalog if c['id'] == 'americas')
track_lonlat = np.asarray(circuit['points'])[:, :2] / projection['factors'] + projection['origin']
locations = np.vstack([land_lonlat.reshape(-1, 2), track_lonlat])
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_TIMEOUT='60'):
    with rasterio.open(url) as source:
        x, y = map(np.asarray, transform('EPSG:4326', source.crs, *locations.T))
        window = from_bounds(x.min()-2, y.min()-2, x.max()+2, y.max()+2, source.transform).round_offsets().round_lengths()
        samples = source.read(1, window=window)
        affine = source.window_transform(window)
        inverse = ~affine
        qx, qy = x*inverse.a+inverse.c-.5, y*inverse.e+inverse.f-.5
        ix, iy = np.floor(qx).astype(int), np.floor(qy).astype(int)
        if ix.min() < 0 or iy.min() < 0 or ix.max()+1 >= samples.shape[1] or iy.max()+1 >= samples.shape[0]:
            raise ValueError('Requested neighborhood exceeds source tile')
        u, v = qx-ix, qy-iy
        neighbors = np.stack([samples[iy, ix], samples[iy, ix+1], samples[iy+1, ix], samples[iy+1, ix+1]])
        if not np.isfinite(neighbors).all() or (source.nodata is not None and (neighbors == source.nodata).any()):
            raise ValueError('Source contains missing elevation samples')
        heights = neighbors[0]*(1-u)*(1-v) + neighbors[1]*u*(1-v) + neighbors[2]*(1-u)*v + neighbors[3]*u*v
track_heights = heights[xx.size:]
data['grid']['heights'] = heights[:xx.size].reshape(shape).round(3).tolist()
data['trackTerrainHeights'] = track_heights.round(3).tolist()
data['trackDatumMeters'] = float(track_heights.min())
data['trackTerrainRangeMeters'] = float(np.ptp(track_heights))
data['source'] = {
    'provider': 'USGS 3DEP 1m, TX Central B1 2017', 'url': url, 'catalogProduct': product,
    'nativeResolutionMeters': 1, 'groundModel': 'National terrain DEM',
    'survey_grade': False, 'road_surface': False, 'retrieved': str(date.today()),
    'license': 'US public domain',
    'method': 'Bilinear sampling of USGS lidar-derived bare-earth terrain; no telemetry',
    'limitations': '2017 acquisition; current road banking, resurfacing and structures not guaranteed. Grid displayed at 15m spacing.',
}
(folder / 'americas.json').write_text(json.dumps(data, separators=(',', ':')))
np.savez_compressed(folder / 'americas-source.npz', heights=samples, transform=np.asarray(tuple(affine)))
print('Austin USGS ground range:', float(np.ptp(track_heights)), 'metres')
