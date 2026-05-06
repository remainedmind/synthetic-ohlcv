from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from synthetic_klines.config import CycleComponent, SyntheticKlinesConfig

ControlInput = Literal["checkbox", "number", "select", "slider", "text"]

CONFIG_CONTROL_PATHS = {
    "rows",
    "seed",
    "base_price",
    "start_timestamp",
    "interval_ms",
    "linear_bias",
    "noise_std",
    "cycles[].kind",
    "cycles[].amplitude",
    "cycles[].period",
    "cycles[].phase",
    "cycles[].decay",
    "regime_shift.enabled",
    "regime_shift.count",
    "regime_shift.amplitude",
    "regime_shift.transition_steps",
    "gap_noise_std",
    "wick_scale",
    "range_multiplier",
    "base_volume",
    "volume_noise_std",
    "volume_return_sensitivity",
    "volume_range_sensitivity",
    "volume_volatility_sensitivity",
    "volatility_cluster.enabled",
    "volatility_cluster.strength",
    "volatility_cluster.persistence",
    "jump_shocks.enabled",
    "jump_shocks.probability",
    "jump_shocks.scale",
    "mean_reversion.enabled",
    "mean_reversion.strength",
    "mean_reversion.window",
}


class BaseControlModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ControlOption(BaseControlModel):
    value: str
    label: str


class ControlSpec(BaseControlModel):
    path: str
    label: str
    input: ControlInput
    hint: str
    default: str | int | float | bool
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[ControlOption] = Field(default_factory=list)
    non_slider_reason: str | None = None


class ControlGroup(BaseControlModel):
    key: str
    label: str
    controls: list[ControlSpec]


def control_schema(config: SyntheticKlinesConfig | None = None) -> list[ControlGroup]:
    defaults = config or SyntheticKlinesConfig()
    cycle_defaults = CycleComponent()
    return [
        ControlGroup(
            key="dataset_export",
            label="Dataset & Export",
            controls=[
                _control(
                    "export.dataset_name",
                    "Dataset name",
                    "text",
                    "Output file stem. Use letters, numbers, dots, dashes, or underscores.",
                    "synthetic_klines",
                    non_slider_reason="Text identifier, not a numeric range.",
                ),
                _control(
                    "rows",
                    "Rows",
                    "number",
                    "Number of candles to generate.",
                    defaults.rows,
                    min=2,
                    max=100_000,
                    step=1,
                    non_slider_reason="Exact integer count is easier to type than drag.",
                ),
                _control(
                    "seed",
                    "Seed",
                    "number",
                    "Random seed. Keep it fixed to reproduce the same dataset exactly.",
                    defaults.seed,
                    step=1,
                    non_slider_reason="Exact seed values are identifiers, not magnitudes.",
                ),
                _control(
                    "base_price",
                    "Base price",
                    "number",
                    "Starting price level. It scales OHLC values without changing "
                    "pattern difficulty.",
                    defaults.base_price,
                    min=0.01,
                    step=0.01,
                    non_slider_reason="Price scale often needs exact typed values.",
                ),
                _control(
                    "start_timestamp",
                    "Start timestamp ms",
                    "number",
                    "First candle timestamp in milliseconds. Defaults to a dummy historical date.",
                    defaults.start_timestamp,
                    min=0,
                    step=1,
                    non_slider_reason="Timestamp values require exact entry.",
                ),
                _control(
                    "interval_ms",
                    "Interval ms",
                    "number",
                    "Candle spacing in milliseconds. 900000 means 15-minute candles.",
                    defaults.interval_ms,
                    min=1,
                    step=1,
                    non_slider_reason="Interval values should be exact.",
                ),
            ],
        ),
        ControlGroup(
            key="trend",
            label="Trend",
            controls=[
                _slider(
                    "linear_bias",
                    "Linear bias",
                    "Constant per-step log-return drift. Positive values create steady "
                    "growth; zero disables it.",
                    defaults.linear_bias,
                    min=-0.001,
                    max=0.001,
                    step=0.00001,
                ),
                _slider(
                    "noise_std",
                    "Return noise",
                    "Random log-return noise. Higher values make the pattern harder to "
                    "learn; zero removes it.",
                    defaults.noise_std,
                    min=0.0,
                    max=0.01,
                    step=0.0001,
                ),
                _control(
                    "cycles[].kind",
                    "Cycle kind",
                    "select",
                    "Wave shape for a repeating bull/bear component.",
                    cycle_defaults.kind,
                    options=[
                        ControlOption(value="sine", label="Sine"),
                        ControlOption(value="cosine", label="Cosine"),
                    ],
                    non_slider_reason="Choice between supported wave families.",
                ),
                _slider(
                    "cycles[].amplitude",
                    "Cycle amplitude",
                    "Per-step wave contribution. Higher values make cycles stronger; "
                    "zero disables this cycle.",
                    cycle_defaults.amplitude,
                    min=0.0,
                    max=0.01,
                    step=0.0001,
                ),
                _control(
                    "cycles[].period",
                    "Cycle period",
                    "number",
                    "Cycle length in candles. Shorter periods repeat more often in the "
                    "training split.",
                    cycle_defaults.period,
                    min=2,
                    step=1,
                    non_slider_reason="Periods should be exact candle counts.",
                ),
                _slider(
                    "cycles[].phase",
                    "Cycle phase",
                    "Horizontal wave offset in radians. Use it to shift where a cycle starts.",
                    cycle_defaults.phase,
                    min=-6.283,
                    max=6.283,
                    step=0.01,
                ),
                _slider(
                    "cycles[].decay",
                    "Cycle decay",
                    "Fades the cycle over the dataset. Higher values weaken later "
                    "repetitions; zero keeps it stable.",
                    cycle_defaults.decay,
                    min=0.0,
                    max=3.0,
                    step=0.01,
                ),
                _control(
                    "regime_shift.enabled",
                    "Regime shifts",
                    "checkbox",
                    "Adds smooth bull/bear drift changes. Turn off for a stationary benchmark.",
                    defaults.regime_shift.enabled,
                    non_slider_reason="Boolean on/off switch.",
                ),
                _slider(
                    "regime_shift.count",
                    "Regime count",
                    "Number of drift regimes. More regimes increase nonstationarity.",
                    defaults.regime_shift.count,
                    min=1,
                    max=20,
                    step=1,
                ),
                _slider(
                    "regime_shift.amplitude",
                    "Regime amplitude",
                    "Strength of regime drift. Higher values create clearer bull/bear "
                    "phases; zero disables impact.",
                    defaults.regime_shift.amplitude,
                    min=0.0,
                    max=0.002,
                    step=0.00001,
                ),
                _control(
                    "regime_shift.transition_steps",
                    "Transition steps",
                    "number",
                    "Candles used to blend between regimes. Larger values make "
                    "transitions smoother.",
                    defaults.regime_shift.transition_steps,
                    min=1,
                    step=1,
                    non_slider_reason="Transition width should be an exact candle count.",
                ),
            ],
        ),
        ControlGroup(
            key="candle_shape",
            label="Candle Shape",
            controls=[
                _slider(
                    "gap_noise_std",
                    "Gap noise",
                    "Open-price noise around the previous close. Higher values create "
                    "more visible candle gaps.",
                    defaults.gap_noise_std,
                    min=0.0,
                    max=0.005,
                    step=0.00001,
                ),
                _slider(
                    "wick_scale",
                    "Wick scale",
                    "Controls extra high/low tails. Higher values create longer wicks; "
                    "zero removes extra wicks.",
                    defaults.wick_scale,
                    min=0.0,
                    max=3.0,
                    step=0.05,
                ),
                _slider(
                    "range_multiplier",
                    "Range multiplier",
                    "Scales candle high-low range. Higher values increase intrabar volatility.",
                    defaults.range_multiplier,
                    min=0.0,
                    max=5.0,
                    step=0.05,
                ),
            ],
        ),
        ControlGroup(
            key="volume",
            label="Volume",
            controls=[
                _control(
                    "base_volume",
                    "Base volume",
                    "number",
                    "Baseline activity level before return/range/volatility effects.",
                    defaults.base_volume,
                    min=0.01,
                    step=1,
                    non_slider_reason="Volume scale often needs exact typed values.",
                ),
                _slider(
                    "volume_noise_std",
                    "Volume noise",
                    "Random volume variation. Higher values make activity less "
                    "deterministic; zero removes it.",
                    defaults.volume_noise_std,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                ),
                _slider(
                    "volume_return_sensitivity",
                    "Return sensitivity",
                    "How much large price moves increase volume. Set zero to ignore returns.",
                    defaults.volume_return_sensitivity,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                ),
                _slider(
                    "volume_range_sensitivity",
                    "Range sensitivity",
                    "How much wide candles increase volume. Set zero to ignore high-low range.",
                    defaults.volume_range_sensitivity,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                ),
                _slider(
                    "volume_volatility_sensitivity",
                    "Volatility sensitivity",
                    "How much latent volatility increases volume. Set zero to ignore "
                    "volatility clustering.",
                    defaults.volume_volatility_sensitivity,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                ),
            ],
        ),
        ControlGroup(
            key="advanced_complexity",
            label="Advanced Complexity",
            controls=[
                _control(
                    "volatility_cluster.enabled",
                    "Volatility clustering",
                    "checkbox",
                    "Makes noise arrive in calm and active phases. Turn off for uniform noise.",
                    defaults.volatility_cluster.enabled,
                    non_slider_reason="Boolean on/off switch.",
                ),
                _slider(
                    "volatility_cluster.strength",
                    "Cluster strength",
                    "How strongly latent volatility amplifies return noise. Zero "
                    "disables contribution.",
                    defaults.volatility_cluster.strength,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                ),
                _slider(
                    "volatility_cluster.persistence",
                    "Cluster persistence",
                    "How long volatility phases last. Higher values create slower "
                    "volatility regimes.",
                    defaults.volatility_cluster.persistence,
                    min=0.0,
                    max=0.99,
                    step=0.01,
                ),
                _control(
                    "jump_shocks.enabled",
                    "Jump shocks",
                    "checkbox",
                    "Adds rare jump returns. Turn off for a smoother benchmark.",
                    defaults.jump_shocks.enabled,
                    non_slider_reason="Boolean on/off switch.",
                ),
                _slider(
                    "jump_shocks.probability",
                    "Jump probability",
                    "Chance of a jump on each candle. Higher values create more "
                    "discontinuities; zero disables jumps.",
                    defaults.jump_shocks.probability,
                    min=0.0,
                    max=0.10,
                    step=0.001,
                ),
                _slider(
                    "jump_shocks.scale",
                    "Jump scale",
                    "Typical jump size. Higher values make shocks more disruptive; zero "
                    "disables jump magnitude.",
                    defaults.jump_shocks.scale,
                    min=0.0,
                    max=0.05,
                    step=0.001,
                ),
                _control(
                    "mean_reversion.enabled",
                    "Mean reversion",
                    "checkbox",
                    "Pulls price back toward a rolling log-price mean. Turn off for "
                    "pure trend-following patterns.",
                    defaults.mean_reversion.enabled,
                    non_slider_reason="Boolean on/off switch.",
                ),
                _slider(
                    "mean_reversion.strength",
                    "Reversion strength",
                    "Pull strength toward the rolling mean. Higher values fight "
                    "persistent trends; zero disables it.",
                    defaults.mean_reversion.strength,
                    min=0.0,
                    max=0.20,
                    step=0.005,
                ),
                _control(
                    "mean_reversion.window",
                    "Reversion window",
                    "number",
                    "Rolling candle count used as the mean-reversion anchor.",
                    defaults.mean_reversion.window,
                    min=2,
                    step=1,
                    non_slider_reason="Window size should be an exact candle count.",
                ),
            ],
        ),
    ]


def control_schema_payload(config: SyntheticKlinesConfig | None = None) -> list[dict[str, Any]]:
    return [group.model_dump(mode="json") for group in control_schema(config)]


def _slider(
    path: str,
    label: str,
    hint: str,
    default: int | float,
    *,
    min: float,
    max: float,
    step: float,
) -> ControlSpec:
    return _control(
        path,
        label,
        "slider",
        hint,
        default,
        min=min,
        max=max,
        step=step,
    )


def _control(
    path: str,
    label: str,
    input: ControlInput,
    hint: str,
    default: str | int | float | bool,
    *,
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
    options: list[ControlOption] | None = None,
    non_slider_reason: str | None = None,
) -> ControlSpec:
    return ControlSpec(
        path=path,
        label=label,
        input=input,
        hint=hint,
        default=default,
        min=min,
        max=max,
        step=step,
        options=options or [],
        non_slider_reason=non_slider_reason,
    )
