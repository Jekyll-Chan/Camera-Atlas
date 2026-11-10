# Geographic data providers

## Offline schema

Supply a WGS84 FeatureCollection without legacy `crs`. Every feature needs `properties.source_id` and a `kind`: water, coastline, contour, road, trail, river, boundary or place. Name fields are `name` and `name:en`; only supplied names can render. Contours have `elevation_m`.

```json
{
  "type": "FeatureCollection",
  "sources": [{
    "id": "survey", "dataset": "Your authorized dataset", "version": "2026-01",
    "url": "https://your-provider.example/dataset", "license": "Dataset license",
    "attribution": "Required visible credit", "retrieved_at": "2026-01-01T00:00:00Z"
  }],
  "features": []
}
```

The empty feature list intentionally draws nothing. Add actual provider geometry, never illustrative hand-drawn shapes passed off as real data. See `examples/data/lucerne.geojson` for a real extract. Optional `location` has `name,lat,lon,accuracy,coordinate_source,source_id`; `locality` and `regional` do not imply camera coordinates. `min_span_km` suppresses rendering below source-appropriate overview scales. Source hashes describe their declared artifact; output includes separate input artifact hashes.

## OpenStreetMap

`Overpass` obtains highway/waterway/water/coastline/boundary ways and place nodes, checks geometry, retains OSM IDs/URLs, dataset timestamps and response hash. It deliberately omits relation assembly: some large lake outlines or complex boundaries may be absent. No invented ring closure or topology repair. Query extent is limited to one degree per side, timeout 25s, identified client, SQLite cache and 2s minimum between requests. Public service is for occasional small interactive use; production/high-volume users must configure their own endpoint or use legal extracts. [Resource guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).

Nominatim-compatible lookup is configured by `--nominatim-url` and never defaults to the public service. More than one result remains unresolved. See the prominent [public Nominatim restrictions](https://operations.osmfoundation.org/policies/nominatim/) in the README before selecting that host. No autocomplete or batch public-geocoding facility is supplied. [OSM copyright](https://www.openstreetmap.org/copyright), ODbL and visible attribution apply to both map geometry and geocoded positions.

## Natural Earth

`NaturalEarth` reads declared local extracts and requires minimum map span. Generalized 1:10m means nominal cartographic scale, not 10-meter positional accuracy. The included European lake source is version 5.0.0, with a conservative 60km minimum span for these illustrations. Different layers need their own informed thresholds. [Terms](https://www.naturalearthdata.com/about/terms-of-use/): public domain. There is no automatic global Natural Earth downloader.

## DEM

Install terrain extra; provide `--dem` plus `--dem-source` JSON with the same Source schema, `units: "m"`, and preferably SHA256. A CRS is required; rotated grids must be warped first; nodata is masked; scale/offset metadata is applied. Contourpy computes geometry at real raster cell centers and pyproj converts to WGS84. Up to 16 million cells and 1000 levels are allowed. No arbitrary contour generation exists.

Copernicus, SRTM, NASADEM and OpenTopography acquisition are not integrated online. Acquire legally, subset with rasterio/GDAL, document license/version/vertical datum, then supply locally. No key is required for this local pipeline. Example terrain is a nearest-neighbor overview subset from [Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/); its full source-specific [attribution notice](../examples/data/TERRAIN-ATTRIBUTION.md) is included. Europe may include EU-DEM/Copernicus and global USGS products; it is not mislabeled as pure SRTM.

## Extending

Implement `Provider.fetch(bounds)` returning validated `GeoData`. Use `CachedHTTP` for bounded retries (three attempts, exponential backoff, Retry-After cap), offline cache and identified requests. New providers must supply terms and source metadata. Provider failures become a clean photograph only when the pipeline handles `ProviderError`; invalid supplied data is a user-visible input error.
