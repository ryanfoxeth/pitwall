# Pitwall Spatial

A self-hosted Formula 1 tabletop for Apple Vision Pro: moving vehicles, four visual themes, leader/followed-driver trails, independent data windows, manual TV synchronization, and adjustable vehicle size.

This repository contains the native visionOS app and its Node.js data server. Each installation uses its owner's OpenF1 account. No StarDeck service, database, account, or credential is required.

## Quick start: server

Requires Node.js 22 or later.

```sh
cd server
npm ci
cp .env.example .env
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Generate two different keys with that command and put them in `PITWALL_KEY` (administrative API access) and `PITWALL_DEVICE_KEY` (read-only device endpoint). Do not commit `.env`. Add your own `OPENF1_USERNAME` and `OPENF1_PASSWORD`; enable `OPENF1_LIVE_ENABLED=true` for your paid real-time subscription. These are OpenF1 account credentials, not a permanent API key: the server exchanges them for expiring OAuth tokens and refreshes them automatically.

```sh
npm test
npm start
```

The default listens only on `127.0.0.1:3000`. Put it behind an HTTPS reverse proxy reachable from your headset. For a container or hosted deployment set `HOST=0.0.0.0`. Keep `/api/f1` private using the supplied access keys; do not share or publicly rebroadcast your paid data feed. `/health` is the only unauthenticated endpoint.

## Quick start: Vision Pro

Requires macOS, Xcode with visionOS SDK/device support, XcodeGen, and Apple signing credentials for a physical headset. Current source was built with Xcode 27; deployment target is visionOS 26.0, which provides native single-instance Controls and tabletop windows.

```sh
cd visionos
xcodegen generate
open PitwallVision.xcodeproj
```

Select your own signing team and unique bundle identifier in Xcode, choose your paired Vision Pro, then Run. In Controls enter the full HTTPS device endpoint (`https://YOUR-HOST/api/f1/device`) and your `PITWALL_DEVICE_KEY`, then save the connection key. The app stores that key in Keychain. The server URL contains no credentials. Open the tabletop and whichever floating panels you want.

Use native volume handles to size/place the track. **Vehicle size** scales every car, lightcycle and block together (0.1–4×). **TV delay** and pause/resume manually align telemetry to your broadcast; there is no automatic Apple TV synchronization or video feed included.

## Historical replay

Select **Historical replay** in Controls to browse completed 2026 practices, qualifying sessions, sprints and Grands Prix. **Download & play** loads the selected session; **Download all** caches the available season on that device, prioritizing races. Keep Pitwall open while downloading. Cancel/retry preserves completed chunks. Archives are downloaded directly from OpenF1, not redistributed in this repository.

The tabletop, timing, tires and other panels share the replay clock. Replay telemetry uses the selected session. The importer uses the actual finish and last completed lap so red flags and delays do not truncate races at their scheduled end. Car positions are sampled at 1 Hz and interpolated only across short gaps. Missing observations remain missing, and partial coverage is labeled. Availability is not guaranteed: Monaco 2026 has extensive missing positions even though lap timing continues.

Monaco and the nine remaining-season circuit replays are registered to the detailed scenery using a completed recorded lap. Registration preserves lateral XY positions and applies the modeled road elevation; it is approximate, not surveyed. Poor fits are rejected and retain the provider-coordinate outline. Other circuits use their recorded outline. Existing saved, unregistered archives are upgraded when opened if a valid fit is available. A privately supplied `Monaco2025Replay.json` enables a clearly labeled 2025 alternative; it is never presented as 2026.

For a bundled archive or command-line import:

```sh
cd visionos
python3 tools/fetch_replay.py 11369
xcodegen generate
```

This writes the ignored `Sources/Resources/MadridReplay.json` (legacy filename; content follows the supplied session ID). An optional second argument selects another output path. Rebuild after adding bundled archives. Historical availability and rate limits are controlled by OpenF1. Run `sh tools/check_replay_registration.sh` to check registration math; native DEBUG `--validate-replay` checks moving recorded cars and the three detailed Monaco environments with a supplied registered Monaco archive.

## Optional lightcycle models

Base installation includes Kenney CC0 kart/scenery and original formula-car geometry. Highlighted Tron vehicles use blocks until you supply the optional models. To reproduce the enhanced Tron theme, download GLB files from:

- [Tron Light Cycle by Firestar](https://sketchfab.com/3d-models/tron-light-cycle-083076c8a3644b088ce7f1e107a12ca6) → `visionos/Assets/Source/Lightcycles/Firestar.glb`
- [Lightcycle by SpringSociety](https://sketchfab.com/3d-models/lightcycle-aaebbf5d4c504dbbb8963f3dd91b37c1) → `visionos/Assets/Source/Lightcycles/SpringSociety.glb`

Both listings identify CC BY 4.0; review their source/license terms for your use. They are intentionally not redistributed here. Run Blender 5.2:

```sh
cd visionos
mkdir -p Evidence
blender --background --python tools/prepare_lightcycles.py
xcodegen generate
```

P1 uses Firestar; the followed driver uses SpringSociety; other drivers use blocks. Only the unique leader/followed drivers have trails. Conversion preserves materials, normalizes geometry, and removes the source's separate trail. Credits and license links remain in the app.

## Data and endpoints

- `/api/f1/device`: `Authorization: Bearer DEVICE_KEY`; compact session, timing, positions, tires, telemetry, weather and recent event feeds.
- `/api/f1/status`, `/api/f1/season/:year`, `/api/f1/data/:topic`, `/api/f1/stream`: `x-api-key: ADMIN_KEY`.
- Server supports all 18 OpenF1 topics; historical cache, bounded requests, rate-limit retries, MQTT live snapshots and session isolation are retained.
- Calendar/results use Jolpica. Official live timing enrichment is separately opt-in with `PITWALL_OFFICIAL_ENABLED=true`; this is an unsupported independent provider, not part of OpenF1 access. It can supply retirement/pit flags missing from OpenF1's live position feed. Check applicable provider terms before enabling it. No status is inferred from a stopped car.

## Scope and limits

This first package is Vision Pro plus the shared data server. StarDeck's integrated iPhone and Rabbit clients are not included. The pure session/qualifying notification event logic is included and tested, but StarDeck-specific APNs delivery, device registry and database inbox are not. There is no push delivery in this standalone release yet.

No live race was available during packaging: tests cover fixtures, auth, caching, updates and events; successful builds do not establish live-race behavior on every circuit. Live outlines for Monaco and the nine remaining-season circuits are registered to the catalog when a sufficiently accurate fit is available; unmatched feeds retain the provider outline. Data/asset licenses and account access are separate from the code license. This is unofficial and not affiliated with Formula 1, OpenF1, Disney or Nintendo.

## Development

```sh
cd server && npm ci && npm test
cd ../visionos
xcodegen generate
xcodebuild -project PitwallVision.xcodeproj -scheme PitwallVision -destination 'generic/platform=visionOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

See `THIRD_PARTY.md` for asset provenance. Do not commit generated race archives, imported optional models, `.env`, signing files, or device credentials.

## 2026 offline track library

The app starts in **Track library** with **Follow current race week** enabled. It selects the race in the current Monday–Sunday UTC week, or the next race between events; after the season it retains the final circuit. Selecting a circuit manually disables automatic selection until the toggle is enabled again. Live and replay selections are not interrupted. Choose **Source → Track library** in Controls to return. Upcoming races appear first; **Include earlier races** reveals the full 23-race calendar snapshot (17 September 2026). Select a circuit to open its tabletop, then switch among all four themes. The next race in this snapshot is Baku, followed by Sepang, Singapore, Austin, Mexico City, Interlagos, Las Vegas, Lusail and Yas Marina.

These are reference circuit outlines projected into local meters. Twenty-two of the 23 circuits include approximate recorded elevation: Monaco retains its 2025 profile, Madrid uses the existing 2026 replay, and 20 others use 2024 qualifying profiles compared across at least three laps from two drivers. Sepang uses a separate 30 m SRTM terrain estimate, not recorded car or surveyed road elevation. These are not surveyed road surfaces. See [elevation provenance and rebuilding](visionos/ELEVATION.md). Decorative terrain is not surveyed geography and layouts may differ from this season. No cars or race telemetry appear in track previews. Live and replay feeds use detailed catalog scenery after successful coordinate registration; poor or incomplete fits retain provider-coordinate geometry. Race dates in the bundled calendar are UTC calendar dates. Historical archives are downloaded on demand, rather than bundled for every track.

Circuit geometry: bacinger/f1-circuits (MIT); circuit metadata: f1db/f1db, license included with resources. Calendar: Jolpica snapshot. See `visionos/Sources/Resources/Season2026.json` and the adjacent license files.

## Remaining-season surroundings

Baku, Sepang, Singapore, Austin, Mexico City, Interlagos, Las Vegas, Lusail and Yas Marina include mapped buildings, water and characteristic landmarks. Grand Prix, Tron and Retro Kart have separate scenery assets; F1 Miniature shares the Grand Prix environment. All use the same geographic frame and road alignment.

See [sources, accuracy limits and rebuilding](visionos/Assets/Season/README.md). These are geographically grounded tabletop interpretations, not surveyed architectural reconstructions.
