from datetime import datetime, timezone
from urllib.parse import urlparse

from pyproj import Geod

from .http import ProviderError
from .models import Location, Source
from .providers import OSM_ATTRIBUTION, OSM_LICENSE

GEOD=Geod(ellps="WGS84")


def geocode(name, http, url, accept_public=False):
    if not url:
        raise ProviderError("Place-name lookup needs --nominatim-url, a configured provider, or offline location")
    if urlparse(url).hostname == "nominatim.openstreetmap.org" and not accept_public:
        raise ProviderError("Public Nominatim needs deliberate policy acceptance: --accept-public-nominatim-policy")
    result=http.json(url.rstrip("/")+"/search",params={"q":name,"format":"jsonv2","limit":5,
        "addressdetails":1,"accept-language":"en"})
    raw=result["body"]
    source=Source(id="geocoder",dataset="Nominatim / OpenStreetMap",version="query snapshot",
        url=url,license=OSM_LICENSE,attribution=OSM_ATTRIBUTION,
        retrieved_at=datetime.fromtimestamp(result["retrieved_at"],timezone.utc))
    # Multiple results always require disambiguation; popularity is not a reliable identity test.
    candidates=[{"name":x["display_name"],"lat":float(x["lat"]),"lon":float(x["lon"]),
                 "osm_type":x.get("osm_type"),"osm_id":x.get("osm_id")} for x in raw]
    if len(raw)!=1:
        return Location(name=name,candidates=candidates),source
    item=raw[0]
    b=item.get("boundingbox")
    bounds=(float(b[2]),float(b[0]),float(b[3]),float(b[1])) if b else None
    return Location(name=item["display_name"],lat=float(item["lat"]),lon=float(item["lon"]),
        accuracy="locality",coordinate_source="Nominatim place centroid; not camera position",
        source_id=source.id,bounds=bounds),source


def resolve(config, exif_gps, data, http):
    warnings=[]
    source=None
    if config.lat is not None:
        location=Location(name=config.location or "User coordinates",lat=config.lat,lon=config.lon,
            accuracy="regional" if config.confirmed_region else "exact_gps",
            coordinate_source="user-confirmed region center" if config.confirmed_region else "explicit user GPS")
    elif config.location:
        if data.location and data.location.name.casefold()==config.location.casefold():
            location=data.location.model_copy(deep=True)
        else:
            try:
                location,source=geocode(config.location,http,config.nominatim_url,
                                        config.accept_public_nominatim_policy)
            except ProviderError as exc:
                warnings.append(str(exc))
                location=Location(name=config.location)
    elif exif_gps:
        location=Location(name="EXIF GPS",**exif_gps,accuracy="exact_gps",coordinate_source="EXIF GPS")
    elif data.location:
        location=data.location.model_copy(deep=True)
        # A dataset center is never an exact camera location.
        if location.accuracy=="exact_gps":
            location.accuracy="locality"
            location.coordinate_source="offline dataset location; not camera GPS"
    else:
        location=Location()
    if exif_gps and (config.lat is not None or config.location):
        if location.lat is None:
            location.conflicts.append("Explicit place remains unresolved; EXIF was not silently substituted")
        else:
            distance=GEOD.inv(exif_gps["lon"],exif_gps["lat"],location.lon,location.lat)[2]
            if distance>100:
                location.conflicts.append(f"Explicit input overrides EXIF GPS; centers differ by {distance:.0f} m")
    if source:
        data.sources.append(source)
    if location.source_id and location.source_id not in {s.id for s in data.sources}:
        raise ValueError("Location refers to an unknown provenance source")
    return location,warnings
