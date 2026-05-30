"""
IoT Healthcare Platform - Core Modules

This package contains modular components for the IoT Healthcare Monitoring Platform:
- data_module: Data loading and preprocessing
- ml_module: ML model training and prediction
- visualization_module: Plotly chart generation
- simulation_module: Sensor data simulation
- utils_module: Helper functions and constants
"""

__version__ = "1.0.0"

# Lazy-load submodules so heavy dependencies (sklearn, joblib, plotly, etc.)
# are NOT imported at package load time. This is the key fix for slow Streamlit startup.
# Each submodule is only imported the first time it is actually accessed.

_LAZY_MODULES = {
    "data_module",
    "ml_module",
    "visualization_module",
    "simulation_module",
    "utils_module",
}


def __getattr__(name: str):
    if name in _LAZY_MODULES:
        import importlib
        module = importlib.import_module(f".{name}", package=__name__)
        globals()[name] = module  # cache so subsequent accesses are instant
        return module
    raise AttributeError(f"module 'modules' has no attribute {name!r}")


__all__ = list(_LAZY_MODULES)
