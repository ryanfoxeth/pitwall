# Circuit elevation provenance

Pitwall’s road heights are **approximate recorded car-position profiles**, not surveyed road meshes. Matching multiple laps checks repeatability, not absolute accuracy: drivers share the same provider coordinate system and may share systematic errors. Historical recordings may not describe later layout or resurfacing changes.

The generator preserves the geographic reference outline, aligns each recorded lap independently using horizontal rotation/translation/scale, compares height profiles from two drivers, and takes their median. It rejects incomplete laps, excessive alignment errors, suspicious height ranges and inconsistent profiles. Small median smoothing removes isolated spikes. Relative elevation starts at zero; it is not altitude above sea level. Source coordinates use tenths of metres, as documented by [FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/core.py).

Each entry in `Sources/Resources/Season2026.json` carries its source session, laps, driver IDs, registration error and cross-lap agreement. Monaco retains its previously validated 2025 profile. Other historical profiles use 2024 qualifying; Madrid can be rebuilt from a user-downloaded 2026 replay archive. No raw race archive is included.

## Rebuild

Install Python and NumPy, then run from the repository root:

```sh
python3 visionos/tools/fetch_elevation.py --catalog visionos/Sources/Resources/Season2026.json --cache /tmp/pitwall-elevation-cache --ids baku marina_bay --apply
python3 visionos/tools/check_circuit_catalog.py
```

Omit `--apply` to inspect a report without modifying the catalog. Downloads are cached outside the repository and requests are paced. An optional `--archive /path/to/replay.json` uses a locally downloaded Pitwall replay instead of API requests; use `--ids madring` for the bundled calendar’s Madrid circuit.

## Independent checks and remaining limitations

F1’s [published elevation comparison](https://www.formula1.com/en/latest/article/highs-and-lows-which-f1-track-has-the-most-elevation-changes-.7I9JEcBw3R2AqXbnJ6hyvc.7I9JEcBw3R2AqXbnJ6hyvc) provides historical range checks for many circuits. These are useful corroboration but do not certify the full profile. Sepang is documented there as having 22m of variation; that single number cannot supply a trustworthy full-lap profile.

Public local LiDAR/terrain and openly licensed aerial imagery can improve surrounding terrain and provide independent checks. Road bridges, tunnels and underpasses require special handling; a ground or surface height map alone does not identify the driven road. Google Maps imagery/3D tiles are not bundled or traced: its standard platform terms restrict deriving reusable geometry. Local survey coverage and redistribution terms must be checked per circuit.

## Bundled coverage

22 of 23 circuits have recorded elevation. Sepang has a separate NASA SRTMGL1 v3 terrain estimate sampled through Open Topo Data at 30 m resolution. Its smoothed 28.6 m range is not surveyed road elevation: terrain, embankments and buildings can influence it. The published historical 22 m range is a comparison, not a calibration target. Source observations are retained in `Assets/Season/SepangElevation.json`; rebuild using `python3 visionos/tools/fetch_sepang_terrain.py` after preparing the geographic projection.

| Circuit | Recorded range (m) | Source year |
|---|---:|---:|
| Melbourne Grand Prix Circuit | 2.33 | 2024 |
| Shanghai International Circuit | 6.95 | 2024 |
| Suzuka Circuit | 40.16 | 2024 |
| Miami International Autodrome | 3.3 | 2024 |
| Circuit Gilles Villeneuve | 5.18 | 2024 |
| Circuit de Monaco | 41.9 | 2025 |
| Circuit de Barcelona-Catalunya | 29.7 | 2024 |
| Red Bull Ring | 63.32 | 2024 |
| Silverstone Circuit | 11.12 | 2024 |
| Circuit de Spa-Francorchamps | 102.09 | 2024 |
| Hungaroring | 34.59 | 2024 |
| Circuit Park Zandvoort | 8.7 | 2024 |
| Autodromo Nazionale Monza | 12.4 | 2024 |
| Circuito de Madring | 24.17 | 2026 |
| Baku City Circuit | 26.63 | 2024 |
| Sepang International Circuit | 28.6 (terrain estimate) | SRTMGL1 v3 |
| Marina Bay Street Circuit | 5.15 | 2024 |
| Circuit of the Americas | 29.9 | 2024 |
| Autódromo Hermanos Rodríguez | 2.55 | 2024 |
| Autódromo José Carlos Pace | 42.77 | 2024 |
| Las Vegas Street Circuit | 16.05 | 2024 |
| Lusail International Circuit | 4.09 | 2024 |
| Yas Marina Circuit | 10.88 | 2024 |

## Historical published range cross-check

These 2016 F1 figures corroborate broad height ranges, not current-layout accuracy or point-by-point road height. The largest range difference below is approximately one metre.

| Circuit | Recorded range (m) | Published 2016 range (m) |
|---|---:|---:|
| albert_park | 2.33 | 2.6 |
| shanghai | 6.95 | 7.4 |
| suzuka | 40.16 | 40.4 |
| villeneuve | 5.18 | 5.2 |
| monaco | 41.77 | 42 |
| catalunya | 29.7 | 29.6 |
| red_bull_ring | 63.32 | 63.5 |
| silverstone | 11.12 | 11.3 |
| spa | 102.09 | 102.2 |
| hungaroring | 34.59 | 34.7 |
| monza | 12.4 | 12.8 |
| baku | 26.63 | 26.8 |
| marina_bay | 5.15 | 5.3 |
| americas | 29.9 | 30.9 |
| rodriguez | 2.55 | 2.8 |
| interlagos | 42.77 | 43 |
| yas_marina | 10.88 | 10.7 |
