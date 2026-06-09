from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GeoPoint:
    lat: float
    lon: float

@dataclass
class Plot:
    plot_id: str
    points: List[GeoPoint]          # 1 punto (parcela <4ha) o vértices de polígono
    area_ha: Optional[float] = None

@dataclass
class Lot:
    lot_id: str
    producer_name: str
    cooperative: str
    commodity: str                  # coffee | cocoa
    country: str = "PE"
    region: str = ""
    plots: List[Plot] = field(default_factory=list)
    harvest_season: str = ""
    raw_notes: str = ""

@dataclass
class DeforestationFinding:
    plot_id: str
    risk: str                       # negligible | review | high
    loss_after_cutoff: bool
    detail: str = ""
