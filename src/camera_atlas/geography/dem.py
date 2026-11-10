import hashlib
import json

import numpy as np
from pyproj import Transformer

from .models import GeoData, Source


def contours(path, source_path, interval):
    try:
        import contourpy
        import rasterio
    except ImportError as exc:
        raise ValueError("Install camera-atlas[terrain] for DEM contours") from exc
    source=Source.model_validate(json.loads(source_path.read_text()))
    if source.units!="m":
        raise ValueError("DEM provenance must declare verified elevation units=m")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if source.sha256 and source.sha256!=digest:
        raise ValueError("DEM SHA256 does not match provenance")
    source.sha256=digest
    with rasterio.open(path) as raster:
        if not raster.crs:
            raise ValueError("DEM requires a declared CRS")
        if raster.width*raster.height>16_000_000:
            raise ValueError("Subset the DEM to at most 16 million cells before contouring")
        if raster.transform.b or raster.transform.d:
            raise ValueError("Rotated DEMs must first be warped to a north-up grid")
        z=raster.read(1,masked=True).astype(float)
        z=z*raster.scales[0]+raster.offsets[0]
        if z.count()==0:
            raise ValueError("DEM contains only nodata")
        x=raster.transform.c+(np.arange(raster.width)+.5)*raster.transform.a
        y=raster.transform.f+(np.arange(raster.height)+.5)*raster.transform.e
        if x[0]>x[-1]:
            x=x[::-1];z=z[:,::-1]
        if y[0]>y[-1]:
            y=y[::-1];z=z[::-1,:]
        generator=contourpy.contour_generator(x=x,y=y,z=z,corner_mask=False)
        transformer=Transformer.from_crs(raster.crs,4326,always_xy=True)
        levels=np.arange(np.ceil(float(z.min())/interval)*interval,float(z.max()),interval)
        if len(levels)>1000:
            raise ValueError("Contour interval creates more than 1000 levels")
        features=[]
        for level in levels:
            for line in generator.lines(float(level)):
                if len(line)<2:
                    continue
                lon,lat=transformer.transform(line[:,0],line[:,1])
                coords=np.column_stack((lon,lat)).tolist()
                features.append({"type":"Feature","geometry":{"type":"LineString","coordinates":coords},
                    "properties":{"kind":"contour","elevation_m":float(level),"source_id":source.id}})
    return GeoData(sources=[source],features=features)
