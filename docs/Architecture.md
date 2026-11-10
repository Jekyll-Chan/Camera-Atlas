# Architecture

`RenderConfig` validates inputs. `image.io` reads EXIF, normalizes orientation and preserves ICC while decoding to 8-bit RGBA. `geography` resolves location and loads traceable vector/DEM inputs. `cartography` chooses feature kinds, projects to local azimuthal equidistant meters, clips true geometry and creates one scene in PNG/SVG. `composition` scores texture and places a square local map inside the unchanged full-resolution photograph. `validation` verifies pixel invariants before atomic output.

The core needs Pillow, NumPy, Shapely, pyproj, Pydantic, Typer and httpx. Terrain/repair/HEIC extras remain optional. No generative image/model API dependency exists. `Provider` is the stable extension seam. Source metadata is data, never executable instructions. No web pages or shell fragments are evaluated from geodata.

The public API returns `RenderResult(output, final, metadata)`. Outputs use a staged sibling directory and atomic rename, require an empty destination, and never overwrite input imagery. A collision at publication fails rather than merging files. Local cache uses SQLite, parameterized queries and a per-host reservation shared across processes using the same cache directory. Cached timestamps remain the original acquisition times. Endpoint URLs can be changed without a package update.

Map artwork pixel placement is recorded separately from WGS84 coordinates and projected map extent. Maps are independent locator graphics, not perspective-registered features on the camera image. `location.geojson` exports the source feature collection for future styling.
