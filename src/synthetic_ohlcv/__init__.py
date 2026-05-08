"""Independent synthetic OHLCV kline generator and local preview app."""

from synthetic_ohlcv.config import (
    CycleComponent,
    JumpShockConfig,
    MeanReversionConfig,
    RegimeShiftConfig,
    SyntheticKlinesConfig,
    VolatilityClusterConfig,
)
from synthetic_ohlcv.controls import (
    CONFIG_CONTROL_PATHS,
    ControlGroup,
    ControlOption,
    ControlSpec,
    control_schema,
    control_schema_payload,
)
from synthetic_ohlcv.generator import (
    KLINE_COLUMNS,
    make_synthetic_ohlcv,
    make_synthetic_ohlcv_with_metadata,
)
from synthetic_ohlcv.io import SaveResult, save_synthetic_ohlcv

__version__ = "0.1.3"
__all__ = [
    "CONFIG_CONTROL_PATHS",
    "KLINE_COLUMNS",
    "ControlGroup",
    "ControlOption",
    "ControlSpec",
    "CycleComponent",
    "JumpShockConfig",
    "MeanReversionConfig",
    "RegimeShiftConfig",
    "SaveResult",
    "SyntheticKlinesConfig",
    "VolatilityClusterConfig",
    "__version__",
    "control_schema",
    "control_schema_payload",
    "make_synthetic_ohlcv",
    "make_synthetic_ohlcv_with_metadata",
    "save_synthetic_ohlcv",
]
