# Capability checks and first use

The helper `scripts/onboard.py` uses only Python's standard library. It can diagnose with Python 3.9+, but rendering/setup needs 3.11+. It never installs during `doctor`. A real image-understanding tool is separate from Python/image decoding.

On Agensi, use `get_skill` to fetch this reference, `scripts/onboard.py`, and `references/engine-lock.json`. Write the script unchanged to a temporary file and the JSON to another temporary file. Pass the JSON path with `--lock`; the helper intentionally never assumes resources are beside its temporary script. Do not persist the skill itself or rewrite/shorten its code. Local repository use can run the existing helper directly. Choose a writable task workspace, separate from original photography. User output files and the explicitly installed open-source engine environment can persist; skill scripts and instructions must follow the platform's temporary-delivery rules.

Commands below are agent operations, not homework for a novice. Substitute the actual temporary script/lock paths and Python executable as tool arguments; never invent installed paths.

```bash
python3 /tmp/onboard.py doctor --workspace ./camera-atlas-work
python3.11 /tmp/onboard.py setup --workspace ./camera-atlas-work --lock /tmp/engine-lock.json
python3.11 /tmp/onboard.py demo --workspace ./camera-atlas-work --lock /tmp/engine-lock.json
```

`doctor`: reports Python version, core/optional dependencies and separate offline, region-fill and online readiness. For the agent workflow require `online_ready`, not merely a version label or `offline_ready`. This verifies an importable agent bridge and vector decoder as well as region-fill support. An existing trusted engine can be checked via `--python /actual/path/to/python`; its source trust is still the agent's responsibility. No photo, GPS, environment secrets or web account is read.

`setup`: downloads the immutable official GitHub source ZIP named in the lock, verifies SHA256 before installing, creates a separate `.venv`, installs the engine and checks dependencies. Read the archive size from the lock; dependencies need additional network and disk space. A lock declaring `agent_bridge`, `region_fill` and `online_maps` installs `maps` by default and verifies those capabilities. An unmarked older lock can only prepare its offline demo and must not report the online agent ready. The package version remains 0.1.0, so inspect capabilities rather than that label alone. Setup does not install a model service, upload photos or create a paid account. It refuses an unmanaged existing `.venv`. If setup is already authorized, do not ask again. If installation is unavailable, offer the clearly labeled planning route. `--source-archive` accepts a previously downloaded archive only when its checksum matches. Add `--extra terrain`, `--extra repair`, or `--extra heic` only for an actual need.

`demo`: retrieves checksum-verified NASA photo, Natural Earth lake GeoJSON and photo notices from the pinned official repository, then renders offline. Returns exact final/overlay/provenance paths and warnings. It downloads no private imagery and makes no public geocoder/Overpass request. NASA aerial photography is an engineering sample, not ground-level travel photography. The sample is a locality locator, never an astronaut's ground camera point. Existing outputs and changed inputs are never overwritten.

After setup, use the returned Python path for the photo/place workflow in [agent-workflow.md](agent-workflow.md):

```bash
/path/returned/by/doctor -m camera_atlas.agent prepare --input /actual/photo.jpg --workspace /actual/private-task
```

Then resolve the user's place, inspect/refine the region and render actual files. Never reuse the public demo's location or data for another photograph. Keep setup failures actionable: say what is unavailable, preserve the photo, and offer a plan or another code-enabled agent; do not dump raw installation logs on a novice.

## Region-fill capability

The doctor reports `region_fill_supported`, `agent_bridge_supported` and `online_ready`. The current workflow needs all three. If only older code is available, explain the missing capability; do not substitute a small corner map and call the task complete. Keep the immutable revision and checksum unchanged during normal use. Updating that pin is a release operation requiring source verification and fresh-install testing.
