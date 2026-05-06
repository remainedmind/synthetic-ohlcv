from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_INTERVAL_MS = 15 * 60 * 1000
DEFAULT_START_TIMESTAMP = 1_609_459_200_000
DEFAULT_EXPORT_DIR = Path("exports")

CycleKind = Literal["sine", "cosine"]


class BaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CycleComponent(BaseConfig):
    kind: CycleKind = "sine"
    amplitude: float = Field(default=0.0014, ge=0.0)
    period: int = Field(default=96, ge=2)
    phase: float = 0.0
    decay: float = Field(default=0.0, ge=0.0)


class RegimeShiftConfig(BaseConfig):
    enabled: bool = False
    count: int = Field(default=3, ge=1, le=20)
    amplitude: float = Field(default=0.00025, ge=0.0)
    transition_steps: int = Field(default=48, ge=1)


class VolatilityClusterConfig(BaseConfig):
    enabled: bool = False
    strength: float = Field(default=0.35, ge=0.0)
    persistence: float = Field(default=0.92, ge=0.0, lt=1.0)


class JumpShockConfig(BaseConfig):
    enabled: bool = False
    probability: float = Field(default=0.002, ge=0.0, le=1.0)
    scale: float = Field(default=0.006, ge=0.0)


class MeanReversionConfig(BaseConfig):
    enabled: bool = False
    strength: float = Field(default=0.025, ge=0.0, le=1.0)
    window: int = Field(default=96, ge=2)


def default_cycles() -> list[CycleComponent]:
    return [
        CycleComponent(kind="sine", amplitude=0.0014, period=96, phase=0.0),
        CycleComponent(kind="cosine", amplitude=0.00045, period=672, phase=0.75),
    ]


class SyntheticKlinesConfig(BaseConfig):
    rows: int = Field(default=4_000, ge=2, le=100_000)
    seed: int = 43
    base_price: float = Field(default=10_000.0, gt=0.0)
    start_timestamp: int = Field(default=DEFAULT_START_TIMESTAMP, ge=0)
    interval_ms: int = Field(default=DEFAULT_INTERVAL_MS, gt=0)

    linear_bias: float = 0.00002
    noise_std: float = Field(default=0.0008, ge=0.0)
    gap_noise_std: float = Field(default=0.00012, ge=0.0)
    wick_scale: float = Field(default=0.55, ge=0.0)
    range_multiplier: float = Field(default=1.35, ge=0.0)

    base_volume: float = Field(default=1_000.0, gt=0.0)
    volume_noise_std: float = Field(default=0.12, ge=0.0)
    volume_return_sensitivity: float = Field(default=0.35, ge=0.0)
    volume_range_sensitivity: float = Field(default=0.20, ge=0.0)
    volume_volatility_sensitivity: float = Field(default=0.20, ge=0.0)

    cycles: list[CycleComponent] = Field(default_factory=default_cycles)
    regime_shift: RegimeShiftConfig = Field(default_factory=RegimeShiftConfig)
    volatility_cluster: VolatilityClusterConfig = Field(default_factory=VolatilityClusterConfig)
    jump_shocks: JumpShockConfig = Field(default_factory=JumpShockConfig)
    mean_reversion: MeanReversionConfig = Field(default_factory=MeanReversionConfig)

    @field_validator("linear_bias")
    @classmethod
    def validate_finite_linear_bias(cls, value: float) -> float:
        if not -1.0 < value < 1.0:
            raise ValueError("linear_bias must be between -1.0 and 1.0")
        return value

    @model_validator(mode="after")
    def validate_component_scale(self) -> "SyntheticKlinesConfig":
        max_cycle_amplitude = max((cycle.amplitude for cycle in self.cycles), default=0.0)
        if max_cycle_amplitude >= 1.0:
            raise ValueError("cycle amplitude must be smaller than 1.0")
        return self
