"""
IRMDS Modules — Domain-specific anomaly detection pipelines.

Each sub-package (visual, network, timeseries, infrastructure) contains
a self-contained pipeline that inherits from `core.base_module.BaseModule`.
Modules are auto-discovered by the PluginRegistry at startup.

To add a new module:
    1. Create a new sub-package under modules/
    2. Add a pipeline.py with a class inheriting BaseModule
    3. The registry will discover and register it automatically
"""
