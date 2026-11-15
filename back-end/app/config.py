"""Configuração vinda do ambiente, lida ao criar o app (não no import). Nada de segredo em código."""
import os
from dataclasses import dataclass, field

env = lambda name, default=None: field(default_factory=lambda: os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    release_dir: str = env('FV_RELEASE', '../serving/release')
    cache_path: str = env('FV_CACHE', 'cache.db')
    map_key: str | None = env('FIRMS_MAP_KEY')
    anthropic_key: str | None = env('ANTHROPIC_API_KEY')
    cors_origins: str = env('FV_CORS', '*')                 # separadas por vírgula
    verify_sha: str | None = env('FV_VERIFY_SHA')           # '1' = confere sha256 no boot
    realtime_ttl: int = 3600
