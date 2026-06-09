from .models import Lot, Plot

def plot_geometry(plot: Plot):
    if len(plot.points) == 1:
        p = plot.points[0]
        return {"type": "Point", "coordinates": [p.lon, p.lat]}
    ring = [[p.lon, p.lat] for p in plot.points]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}

def lot_to_geojson(lot: Lot):
    feats = []
    for pl in lot.plots:
        feats.append({
            "type": "Feature",
            "properties": {
                "plot_id": pl.plot_id, "lot_id": lot.lot_id,
                "producer": lot.producer_name, "commodity": lot.commodity,
                "area_ha": pl.area_ha,
            },
            "geometry": plot_geometry(pl),
        })
    return {"type": "FeatureCollection", "features": feats}
