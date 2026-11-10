# Capability checks and first use

The helper `scripts/onboard.py` uses only Python's standard library. It can diagnose with Python 3.9+, but rendering/setup needs 3.11+. It never installs during `doctor`. A real image-understanding tool is separate from Python/image decoding.

On Agensi, use `get_skill` to fetch this reference, `scripts/onboard.py`, and `references/engine-lock.json`. Write the script unchanged to a temporary file and the JSON to another temporary file. Pass the JSON path with `--lock`; the helper intentionally never assumes resources are beside its temporary script. Do not persist the skill itself or rewrite/shorten its code. Local repository use can run the existing helper directly. Choose a writable task workspace, separate from original photography. User output files and the explicitly installed open-source engine environment can persist; skill scripts and instructions must follow the platform's temporary-delivery rules.

Commands below are agent operations, not homework for a novice. Substitute the actual temporary script/lock paths and Python executable as tool arguments; never invent installed paths.

```bash
python3 /tmp/onboard.py doctor --workspace ./camera-atlas-work
python3.11 /tmp/onboard.py setup --workspace ./camera-atlas-work --lock /tmp/engine-lock.json
python3.11 /tmp/onboard.py demo --workspace ./camera-atlas-work --lock /tmp/engine-lock.json
```

`doctor`: reports Python version, core/optional dependencies, readiness and render/setup/plan recommendation. An existing trusted engine can be checked via `--python /actual/path/to/python`; its source trust is still the agent's responsibility. No photo, GPS, environment secrets or web account is read.

`setup`: downloads an immutable official GitHub source ZIP, verifies SHA256 before installing, creates a separate `.venv`, installs engine 0.1.0 and checks dependencies. The source archive is about 61 MB; Python packages need additional network/disk space. It does not install a model service, upload photos or create a paid account. It refuses an unmanaged existing `.venv`. If the request already authorizes setup, do not ask again. If policy/user constraints prohibit installation, use Plan mode. For offline installation, `--source-archive` accepts an already-obtained source ZIP only when its checksum matches. Add `--extra terrain`, `--extra repair`, or `--extra heic` only for an actual requested need.

`demo`: retrieves checksum-verified NASA photo, Natural Earth lake GeoJSON and photo notices from the pinned official repository, then renders offline. Returns exact final/overlay/provenance paths and warnings. It downloads no private imagery and makes no public geocoder/Overpass request. NASA aerial photography is an engineering sample, not ground-level travel photography. The sample is a locality locator, never an astronaut's ground camera point. Existing outputs and changed inputs are never overwritten.

After setup, use the returned Python path:

```bash
/path/returned/by/doctor -m camera_atlas.cli render --input /actual/photo.jpg   --geojson /actual/verified-data.geojson --location 'Verified place name'   --radius-km 45 --svg --output /new/result-directory
```

Map span must match the actual dataset resolution. The example radius is suitable for the bundled Natural Earth overview, not every user location. For original photos, follow rendering.md rather than reusing the demo's location or data. Keep setup failures actionable: say what is unavailable, preserve the photo, offer a plan or another code-enabled agent; do not dump raw pip logs on a novice.
