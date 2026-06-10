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
    quantity: str = ""              # cantidad estimada del lote (p. ej. "1,200 kg")
    coop_id: str = ""               # cooperativa (multi-tenant)
    captured_by: str = ""           # email del usuario que capturó (auditoría)
    created_at: str = ""            # ISO timestamp de captura
    extra: dict = field(default_factory=dict)  # legalidad + comprador (opcional)

@dataclass
class Consignment:
    """Envío / consignación: agrupa N lotes (parcelas de varios productores y regiones)
    en una sola declaración consolidada, como exige el EUDR para una operación comercial."""
    consignment_id: str
    coop_id: str = ""
    name: str = ""                  # ej. "Contenedor Hamburgo #1"
    commodity: str = ""             # coffee | cocoa
    destination: str = ""           # país / puerto de destino UE
    buyer: str = ""                 # operador importador (UE)
    lot_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    created_by: str = ""            # email del usuario que lo creó
    extra: dict = field(default_factory=dict)  # lang, notas

@dataclass
class DeforestationFinding:
    plot_id: str
    risk: str                       # negligible | review | high
    loss_after_cutoff: bool
    detail: str = ""
