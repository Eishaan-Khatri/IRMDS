"""
Plugin registry — auto-discovers and manages domain modules.

On startup, the registry scans the `modules/` package for sub-packages
that contain a `pipeline.py` file with a class inheriting `BaseModule`.
This means adding a new module (Module 5, 6, 7...) requires:

    1. Create modules/my_new_module/pipeline.py
    2. Define a class inheriting BaseModule with `module_id` set
    3. Restart the application — the registry discovers it automatically

No changes to core/, api/, or dashboard/ needed. This is the plugin
architecture that makes IRMDS genuinely extensible.

Usage:
    registry = PluginRegistry(event_bus, metrics, config)
    registry.discover()              # Scan and register
    registry.start_module("visual")  # Start a specific module
    registry.list_modules()          # Get all registered modules
    registry.stop_all()              # Graceful shutdown
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import TYPE_CHECKING

import modules
from core.base_module import BaseModule, ModuleStatus
from core.exceptions import ModuleError, ModuleNotFoundError
from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import IRMDSConfig
    from core.event_bus import EventBus
    from core.metrics_collector import MetricsCollector

log = get_logger("registry")


class PluginRegistry:
    """Discovers, registers, and manages domain module lifecycles.

    The registry owns the mapping of module_id → BaseModule instance.
    It's the single authority for starting, stopping, and querying modules.
    """

    def __init__(
        self,
        event_bus: EventBus,
        metrics: MetricsCollector,
        config: IRMDSConfig,
    ):
        self._event_bus = event_bus
        self._metrics = metrics
        self._config = config
        self._modules: dict[str, BaseModule] = {}

    def discover(self) -> list[str]:
        """Scan the modules/ package and register all valid modules.

        A valid module is a sub-package of `modules` that contains:
            - A `pipeline.py` file
            - At least one class inheriting from `BaseModule`
            - A non-empty `module_id` class attribute

        Returns:
            List of discovered module IDs.
        """
        discovered = []

        # Iterate over all sub-packages in modules/
        for _importer, modname, is_pkg in pkgutil.iter_modules(
            modules.__path__, modules.__name__ + "."
        ):
            if not is_pkg:
                continue

            pipeline_path = f"{modname}.pipeline"
            try:
                pipeline_mod = importlib.import_module(pipeline_path)
            except ImportError:
                # Sub-package exists but has no pipeline.py — skip silently
                log.debug("no_pipeline_found", package=modname)
                continue

            # Find all BaseModule subclasses in pipeline.py
            for _name, cls in inspect.getmembers(pipeline_mod, inspect.isclass):
                if (
                    issubclass(cls, BaseModule)
                    and cls is not BaseModule
                    and cls.module_id  # Must have a non-empty module_id
                ):
                    self._register(cls)
                    discovered.append(cls.module_id)

        log.info("discovery_complete", modules_found=discovered)
        return discovered

    # ─────────────── Module Management ────────────────────

    def start_module(self, module_id: str) -> None:
        """Start a registered module.

        Raises:
            ModuleNotFoundError: If the module_id isn't registered.
        """
        module = self._get_or_raise(module_id)
        module.start()
        log.info("module_started_via_registry", module=module_id)

    def stop_module(self, module_id: str) -> None:
        """Stop a running module.

        Raises:
            ModuleNotFoundError: If the module_id isn't registered.
        """
        module = self._get_or_raise(module_id)
        module.stop()
        log.info("module_stopped_via_registry", module=module_id)

    def restart_module(self, module_id: str) -> None:
        """Restart a module (stop then start).

        Raises:
            ModuleNotFoundError: If the module_id isn't registered.
        """
        module = self._get_or_raise(module_id)
        module.restart()
        log.info("module_restarted_via_registry", module=module_id)

    def start_all(self) -> None:
        """Start all registered modules."""
        for module_id in self._modules:
            try:
                self.start_module(module_id)
            except ModuleError as exc:
                log.error("module_start_failed", module=module_id, error=str(exc))

    def stop_all(self) -> None:
        """Gracefully stop all running modules."""
        for module_id, module in self._modules.items():
            if module.status == ModuleStatus.RUNNING:
                try:
                    module.stop()
                except Exception as exc:
                    log.error("module_stop_failed", module=module_id, error=str(exc))
        log.info("all_modules_stopped")

    # ─────────────── Queries ──────────────────────────────

    def get_module(self, module_id: str) -> BaseModule:
        """Get a module instance by ID.

        Raises:
            ModuleNotFoundError: If the module_id isn't registered.
        """
        return self._get_or_raise(module_id)

    def list_modules(self) -> list[dict]:
        """List all registered modules with their current status.

        Returns:
            List of module state dicts (from BaseModule.to_dict()).
        """
        return [module.to_dict() for module in self._modules.values()]

    def get_running_modules(self) -> list[str]:
        """Get IDs of all currently running modules."""
        return [mid for mid, mod in self._modules.items() if mod.status == ModuleStatus.RUNNING]

    @property
    def module_count(self) -> int:
        """Total number of registered modules."""
        return len(self._modules)

    # ─────────────── Internal ─────────────────────────────

    def _register(self, cls: type[BaseModule]) -> None:
        """Instantiate and register a module class."""
        instance = cls(
            event_bus=self._event_bus,
            metrics=self._metrics,
            config=self._config,
        )
        self._modules[instance.module_id] = instance
        log.info(
            "module_registered",
            module_id=instance.module_id,
            display_name=instance.display_name,
            version=instance.version,
        )

    def _get_or_raise(self, module_id: str) -> BaseModule:
        """Look up a module by ID or raise ModuleNotFoundError."""
        module = self._modules.get(module_id)
        if module is None:
            raise ModuleNotFoundError(module_id)
        return module
