# Grand Prix landscape movies

This optional Blender pipeline builds geographic terrain scenes for every circuit in the bundled catalog. It does not replace the app's currently bundled telemetry-derived road profiles or install app assets. Catalog coverage is not independently certified as the official current calendar.

The output is 16:9 H.264, 1280×720, 24 fps, 60 seconds without audio. A six-second aerial orbit descends for four seconds into one complete 50-second lap. The lead car and camera are staged animation, not historical race positions. Geometry uses metres uniformly on all three axes, with no vertical exaggeration; aerial framing varies by circuit.

## Ground sources

Land heights come from geographic terrain models, never driver Z telemetry:

- Austin: USGS 3DEP 1m lidar-derived terrain, TX Central B1 2017. Direct route samples give about 31.01m of range. The displayed terrain grid is sampled at 15m intervals; this does not make every part of the rendered mesh 1m resolution.
- Monaco: IGN RGE ALTI through Géoplateforme. Route samples give 42.03m of range. Missing surrounding grid cells use GEDTM30, with the fallback mask retained. Sub-sea values are floored at sea level for this land-only scene.
- Other available national terrain: Mapzen Terrain Tiles retains source IDs in HTTP metadata, including USGS NED, Austrian DGM and UK Environment Agency LiDAR.
- Remaining coverage: OpenGeoHub GEDTM30 v1.2, approximately 30m modeled ground elevation, CC-BY-4.0. Small remote COG windows are read; the globe is not downloaded.

These are **not certified road surveys**. Source dates, vegetation/building-removal errors and recent earthworks matter. Road grade is modeled separately: coarse profiles use 45m-sigma smoothing, Monaco's underground road interpolates between mapped portals, and Suzuka's mapped bridge uses an assumed 6m separation. These assumptions remain in each scene's `engineeringNotes`. They do not modify the source land grid. Banking, retaining structures and recent Madrid construction are not verified by this pipeline.

## Reproduce

Requires Blender 5.2, ffmpeg/ffprobe on PATH, and Python with `numpy pillow rasterio shapely>=2.1`. The renderer currently uses Blender's standard macOS application path; edit that path for other systems. Run from repository root. Keep caches outside Git.

```sh
python3 visionos/tools/fetch_season_sources.py /tmp/pitwall-season
python3 visionos/tools/prepare_season_scenery.py /tmp/pitwall-season visionos/Sources/Resources/Season2026.json /tmp/pitwall-all-scenes
python3 visionos/tools/fetch_land_terrain.py --output /tmp/pitwall-land
python3 visionos/tools/fetch_ground_dtm.py /tmp/pitwall-land /tmp/pitwall-ground
python3 visionos/tools/fetch_austin_ground.py /tmp/pitwall-ground
python3 visionos/tools/fetch_monaco_ground.py /tmp/pitwall-ground
python3 visionos/tools/prepare_ground_movies.py /tmp/pitwall-all-scenes /tmp/pitwall-ground /tmp/pitwall-ground-scenes /tmp/pitwall-season
python3 visionos/tools/check_ground_movie_sources.py /tmp/pitwall-ground-scenes
python3 visionos/tools/render_grand_prix_season.py /tmp/pitwall-ground-scenes /path/to/movies
```

Monaco uses the existing attributed `Assets/Monaco/MonacoGeography.json` neighborhood. `Assets/TerrainProjections.json` records the geographic conversion for all catalog layouts and an XY hash that prevents silently using a changed outline with the old projection.

Render one circuit using `--ids americas`. Separate processes must have disjoint circuit IDs and different `--status-name` values. Cache reuse assumes unchanged input data; clear a circuit's derived terrain cache when deliberately changing the catalog or upstream data. Keep source provenance with reused samples.

Each movie folder retains a Blender scene, input JSON, previews, camera collision report, logs, contact sheet, and verification JSON. The renderer checks all 1,440 frames, dimensions, rate and duration, then fully decodes the export before deleting only its own intermediate PNGs. `visualReview: pending` means human/agent visual inspection is still required. A success exit code alone is not visual acceptance. The fixed cinematic speed is intentionally much faster than a real lap.

## Attribution

- [GEDTM30 v1.2, Ho and Hengl (2026)](https://doi.org/10.5281/zenodo.18887460), CC-BY-4.0.
- [USGS National Map](https://www.usgs.gov/the-national-map-data-delivery), US public domain. Product metadata and cropped samples are cached.
- [IGN elevation service](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/calcul-altimetrique/), RGE ALTI; preserve returned source metadata and [Licence Ouverte 2.0 attribution](https://www.data.gouv.fr/datasets/rge-alti-r).
- [Mapzen Terrain Tiles source attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md); source IDs are retained per tile.
- © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL-1.0. Geographic renderings are Produced Works; preserve attribution with publication.
- Circuit outlines © Tomislav Bacinger, [f1-circuits](https://github.com/bacinger/f1-circuits), MIT; see bundled license.

Buildings and landmarks are approximate mapped geometry and original stylized detail. No Google imagery or extracted game assets are included.
