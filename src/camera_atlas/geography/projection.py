import math

import numpy as np
from pyproj import CRS, Transformer
from shapely import transform


class MapProjection:
    def __init__(self, lat, lon, radius_km):
        if abs(lat) > 85:
            raise ValueError("Polar maps above 85° require a dedicated provider/projection")
        self.lat, self.lon = lat, lon
        self.crs = CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m")
        self.forward = Transformer.from_crs(4326, self.crs, always_xy=True)
        self.inverse = Transformer.from_crs(self.crs, 4326, always_xy=True)
        self.radius = radius_km * 1000
        self.extent = (-self.radius, -self.radius, self.radius, self.radius)

    def project(self, geometry):
        return transform(geometry, lambda xy: np.column_stack(self.forward.transform(xy[:, 0], xy[:, 1])))

    def fit_region(self, width, height, anchor=(0.5, 0.5)):
        """Expand the long geographic axis, preserving one metre-to-pixel scale.

        radius remains half the short-axis span. The location at (0, 0) maps to
        anchor within the region; this never changes its geographic coordinates.
        """
        if min(width, height) <= 0 or not all(0 <= a <= 1 for a in anchor):
            raise ValueError("Invalid region dimensions or anchor")
        factor = min(width, height) / (2 * self.radius)
        ax, ay = anchor
        self.extent = (
            -width * ax / factor,
            -height * (1 - ay) / factor,
            width * (1 - ax) / factor,
            height * ay / factor,
        )
        return self

    def bounds_wgs84(self):
        # Projected rectangle edges curve in WGS84; densify all four edges.
        left, bottom, right, top = self.extent
        corners = [
            self.inverse.transform(x, y)
            for t in np.linspace(0, 1, 65)
            for x, y in (
                (left + (right - left) * t, bottom),
                (left + (right - left) * t, top),
                (left, bottom + (top - bottom) * t),
                (right, bottom + (top - bottom) * t),
            )
        ]
        xs, ys = zip(*corners)
        if max(xs) - min(xs) > 180:
            raise ValueError("Antimeridian-crossing bounds require a split offline dataset")
        return min(xs), min(ys), max(xs), max(ys)

    def nice_scale(self, max_m):
        power = 10 ** math.floor(math.log10(max_m))
        return max(v * power for v in (1, 2, 5) if v * power <= max_m)
