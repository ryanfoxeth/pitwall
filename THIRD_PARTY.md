# Third-party data and assets

- Kenney Car Kit / Nature Kit: CC0; exact licenses and source provenance are in `visionos/Assets/Source/`. Converted USDZs retain the original palette textures.
- Optional Firestar / SpringSociety models: user downloads, excluded from Git. Attribution in Controls. The conversion script is included; model ownership is not claimed.
- OpenF1 API and Jolpica data: retrieved by the user's server/account. No archive or provider credential is distributed. See https://openf1.org/docs/ and https://openf1.org/auth.html for current access requirements.
- Official timing adapter: optional independent connection; no uptime or continued access guarantee.
- npm dependencies: licenses available in each installed package and lockfile-resolved source.
- Formula-car geometry, tabletop scenery code and UI: project-authored. Retro Kart uses Kenney models, not Nintendo assets.

- Bundled 2026 circuit reference outlines: https://github.com/bacinger/f1-circuits (MIT; `CircuitGeometryLicense.txt`). Circuit metadata from https://github.com/f1db/f1db (`F1DBLicense.txt`). Outlines projected to local meters and resampled. Twenty-two circuit outlines include approximate elevation derived from OpenF1 recorded location data (https://openf1.org/docs/#location); see `visionos/ELEVATION.md` and per-circuit `elevationSource` metadata for sessions, laps and validation. These profiles are not survey-grade; Sepang uses NASA SRTMGL1 v3 terrain via Open Topo Data, 30 m resolution, explicitly not surveyed road elevation. Calendar snapshot from Jolpica on17 September2026.

- Monaco Grand Prix environment: © OpenStreetMap contributors, ODbL 1.0 geographic database. See `visionos/Assets/Monaco/README.md` for sources, reproducible generation and accuracy limits. This geographic data is not relicensed under the repository MIT code license.

- Remaining-season scenery: © OpenStreetMap contributors, ODbL 1.0. Derived geographic databases, source IDs, attribution and rebuild instructions are in `visionos/Assets/Season/`. USDZ scenery is a produced work; retain attribution. No Google imagery or extracted Google geometry is included.
