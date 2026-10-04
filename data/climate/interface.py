"""Stable climate observation interface; replace providers without changing consumers."""
from abc import ABC, abstractmethod


class ClimateDataProvider(ABC):
    @abstractmethod
    def load_daily(self, location_id: str):
        """Return date-sorted daily dictionaries using the canonical schema."""


class ClimateFeatureProvider(ABC):
    @abstractmethod
    def current_indices(self):
        """Return dated ENSO, IOD and MJO observations with source metadata."""


class WeatherProvider(ABC):
    @abstractmethod
    def ensemble_daily(self, latitude: float, longitude: float, days: int):
        """Return daily weather ensemble members at a coordinate/grid cell."""


class RainfallHistoryProvider(ABC):
    @abstractmethod
    def daily_rainfall(self, latitude: float, longitude: float, start: str, end: str):
        """Return dated observed/reanalysis rainfall and explicit data provenance."""


class AdministrativeBoundaryProvider(ABC):
    @abstractmethod
    def resolve(self, latitude: float, longitude: float):
        """Return only administrative units backed by a geocoder or boundary dataset."""


CANONICAL_FIELDS = (
    "date", "location_id", "latitude", "longitude", "rainfall_mm", "temperature_c",
    "humidity_percent", "wind_kmh", "pressure_hpa", "enso_index", "iod_index",
    "mjo_rmm1", "mjo_rmm2", "mjo_phase", "mjo_amplitude", "normal_rainfall_mm",
    "onset_event", "false_onset_event", "source",
)
