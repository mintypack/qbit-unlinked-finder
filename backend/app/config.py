from __future__ import annotations

from pathlib import Path, PurePath

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class PathMapping(BaseModel):
    from_: str = Field(alias="from")
    to: str


class QbitConfig(BaseModel):
    url: str
    username: str
    password: str = ""
    path_mappings: list[PathMapping] = []


class ScanConfig(BaseModel):
    downloads_root: Path
    incomplete_dir: Path | None = None
    rescan_interval_seconds: int = 900


class DestinationRoot(BaseModel):
    path: Path
    label: str
    categories: list[str] = []


class ServerConfig(BaseModel):
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]


def _nests(a: PurePath, b: PurePath) -> bool:
    return a == b or a.is_relative_to(b) or b.is_relative_to(a)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUF_", env_nested_delimiter="__", populate_by_name=True
    )

    qbittorrent: QbitConfig
    scan: ScanConfig
    destination_roots: list[DestinationRoot]
    server: ServerConfig = ServerConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Env before TOML so any TOML key is overridable from the environment
        return init_settings, env_settings, TomlConfigSettingsSource(settings_cls)

    @model_validator(mode="after")
    def _structural(self) -> "Settings":
        downloads = PurePath(self.scan.downloads_root)
        roots = [PurePath(r.path) for r in self.destination_roots]
        for r in roots:
            if _nests(r, downloads):
                raise ValueError(f"destination root {r} nests with downloads_root")
        for i, a in enumerate(roots):
            for b in roots[i + 1:]:
                if _nests(a, b):
                    raise ValueError(f"destination roots {a} and {b} nest")
        froms = [m.from_ for m in self.qbittorrent.path_mappings]
        if len(froms) != len(set(froms)):
            raise ValueError("duplicate path_mappings.from")
        cats = [c for r in self.destination_roots for c in r.categories]
        if len(cats) != len(set(cats)):
            raise ValueError("category claimed by two destination roots")
        return self


def load_settings(toml_path: Path) -> Settings:
    class _FileSettings(Settings):
        model_config = {**Settings.model_config, "toml_file": str(toml_path)}

    return _FileSettings()


def validate_environment(settings: Settings) -> None:
    # Fatal startup checks that need the real filesystem
    paths = [settings.scan.downloads_root] + [r.path for r in settings.destination_roots]
    for p in paths:
        if not p.is_dir():
            raise ValueError(f"{p} is not a directory")
