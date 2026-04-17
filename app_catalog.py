"""Local macOS app catalog for action-mode app launching."""

from __future__ import annotations

import plistlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import config

_CATALOG_ROOTS: tuple[Path, ...] = (
    Path("/Applications"),
    Path("/System/Applications"),
    Path("/System/Applications/Utilities"),
    Path.home() / "Applications",
)


def _normalize(text: str) -> str:
    """Normalize app names and queries for fuzzy local matching."""
    return "".join(char for char in text.lower() if char.isalnum())


def _read_bundle_id(app_path: Path) -> Optional[str]:
    """Return the bundle identifier from an app bundle when available."""
    info_path = app_path / "Contents" / "Info.plist"
    if not info_path.exists():
        return None
    try:
        with info_path.open("rb") as info_file:
            info = plistlib.load(info_file)
    except (OSError, plistlib.InvalidFileException):
        return None
    bundle_id = info.get("CFBundleIdentifier")
    if isinstance(bundle_id, str) and bundle_id.strip():
        return bundle_id.strip()
    return None


@dataclass(frozen=True)
class AppTarget:
    """Canonical metadata for a launchable macOS app bundle."""

    display_name: str
    path: Path
    bundle_id: Optional[str]

    @property
    def normalized_name(self) -> str:
        """Return the normalized app display name."""
        return _normalize(self.display_name)


@dataclass(frozen=True)
class AppResolution:
    """Outcome of resolving a spoken app query to a local app bundle."""

    status: str
    query: str
    target: Optional[AppTarget] = None
    reason: Optional[str] = None


class AppCatalog:
    """Cache and resolve a small local catalog of installed macOS apps."""

    def __init__(self, logger: Optional[Callable[[str], None]] = None) -> None:
        """Build the initial app catalog from the standard Applications roots."""
        self._logger = logger
        self._targets: list[AppTarget] = []
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the local app catalog from disk."""
        targets: dict[Path, AppTarget] = {}
        for root in _CATALOG_ROOTS:
            if not root.exists():
                continue
            try:
                app_paths = sorted(root.glob("*.app"))
            except OSError:
                continue
            for app_path in app_paths:
                if not app_path.is_dir():
                    continue
                display_name = app_path.stem.strip()
                if not display_name:
                    continue
                targets[app_path] = AppTarget(
                    display_name=display_name,
                    path=app_path,
                    bundle_id=_read_bundle_id(app_path),
                )
        self._targets = sorted(targets.values(), key=lambda target: target.display_name.lower())
        self._log(f"catalog refreshed (apps={len(self._targets)})")

    def resolve(self, query: str) -> AppResolution:
        """Resolve a spoken app query to one local app target."""
        return self._resolve(query, allow_refresh=True)

    def version(self) -> str:
        """Return a simple catalog version string for telemetry."""
        return str(len(self._targets))

    def _resolve(self, query: str, allow_refresh: bool) -> AppResolution:
        """Resolve a query and optionally refresh the catalog once on miss."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return AppResolution(status="unresolved", query=query, reason="empty_query")

        aliased_query = config.APP_NAME_ALIASES.get(cleaned_query.lower(), cleaned_query)
        normalized_query = _normalize(aliased_query)
        exact_matches: list[AppTarget] = []
        partial_matches: list[AppTarget] = []
        for target in self._targets:
            bundle_name = target.bundle_id.split(".")[-1] if target.bundle_id else ""
            normalized_bundle = _normalize(bundle_name)
            normalized_path_name = _normalize(target.path.stem)
            match_values = {
                target.normalized_name,
                normalized_bundle,
                normalized_path_name,
            }
            if normalized_query in match_values:
                exact_matches.append(target)
                continue
            if any(normalized_query and normalized_query in value for value in match_values):
                partial_matches.append(target)

        if len(exact_matches) == 1:
            return AppResolution(status="matched", query=query, target=exact_matches[0])
        if len(exact_matches) > 1:
            return AppResolution(
                status="ambiguous",
                query=query,
                reason="multiple_exact_matches",
            )
        if len(partial_matches) == 1:
            return AppResolution(status="matched", query=query, target=partial_matches[0])
        if len(partial_matches) > 1:
            return AppResolution(
                status="ambiguous",
                query=query,
                reason="multiple_partial_matches",
            )
        if allow_refresh:
            self._log(f"catalog miss for {query!r}; refreshing once")
            self.refresh()
            return self._resolve(query, allow_refresh=False)
        return AppResolution(status="unresolved", query=query, reason="no_match")

    def _log(self, message: str) -> None:
        """Emit an app-catalog log line when a logger is configured."""
        if self._logger is not None:
            self._logger(f"[app_catalog] {message}")
