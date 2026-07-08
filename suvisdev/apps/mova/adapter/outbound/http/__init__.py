"""외부 HTTP API 어댑터 (TMDB, KOFIC 등)."""

from mova.adapter.outbound.http.kofic_adapter import KoficAdapter, KoficAdapterError
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter, TmdbAdapterError

__all__ = [
    "KoficAdapter",
    "KoficAdapterError",
    "TmdbAdapter",
    "TmdbAdapterError",
]
