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

Requires macOS, Xcode with visionOS SDK/device support, XcodeGen, and Apple signing credentials for a physical headset. Current source was built with Xcode 27; deployment target is visionOS 2.0.

```sh
cd visionos
xcodegen generate
open PitwallVision.xcodeproj
```

Select your own signing team and unique bundle identifier in Xcode, choose your paired Vision Pro, then Run. In Controls enter the full HTTPS device endpoint (`https://YOUR-HOST/api/f1/device`) and your `PITWALL_DEVICE_KEY`, then save the connection key. The app stores that key in Keychain. The server URL contains no credentials. Open the tabletop and whichever floating panels you want.

Use native volume handles to size/place the track. **Vehicle size** scales every car, lightcycle and block together (0.1–4×). **TV delay** and pause/resume manually align telemetry to your broadcast; there is no automatic Apple TV synchronization or video feed included.

## Historical replay

Race archives are not redistributed here. Download a historical session directly from OpenF1 using your own access:

```sh
cd visionos
python3 tools/fetch_replay.py 11369
xcodegen generate
```

This writes the ignored `Sources/Resources/MadridReplay.json` (legacy filename; content follows the supplied session ID). Rebuild the app and select Historical replay. Large sessions take time and many rate-limited requests. The importer chooses a completed non-pit-out lap for the outline and keeps actual XYZ samples. It does not invent missing motion or retirements. Replay telemetry fetches the archive's session and start time. Historical availability/rate limits are controlled by OpenF1.

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

No live race was available during packaging: tests cover fixtures, auth, caching, updates and events; successful builds do not establish live-race behavior on every circuit. Live track geometry currently uses the provider's XY outline; replay can include recorded elevation. Data/asset licenses and account access are separate from the code license. This is unofficial and not affiliated with Formula 1, OpenF1, Disney or Nintendo.

## Development

```sh
cd server && npm ci && npm test
cd ../visionos
xcodegen generate
xcodebuild -project PitwallVision.xcodeproj -scheme PitwallVision -destination 'generic/platform=visionOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

See `THIRD_PARTY.md` for asset provenance. Do not commit generated race archives, imported optional models, `.env`, signing files, or device credentials.
