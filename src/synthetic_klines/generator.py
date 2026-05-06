from typing import Any

import numpy as np
import polars as pl

from synthetic_klines.config import (
    CycleComponent,
    SyntheticKlinesConfig,
)

KLINE_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume", "turnover")
EPSILON = 1e-12


def make_synthetic_klines(config: SyntheticKlinesConfig) -> pl.DataFrame:
    frame, _ = make_synthetic_klines_with_metadata(config)
    return frame


def make_synthetic_klines_with_metadata(
    config: SyntheticKlinesConfig,
) -> tuple[pl.DataFrame, dict[str, object]]:
    rng = np.random.default_rng(config.seed)
    index = np.arange(config.rows, dtype=np.float64)

    volatility_multiplier = _volatility_multiplier(config, rng)
    component_returns: dict[str, np.ndarray] = {
        "linear_bias": np.full(config.rows, config.linear_bias, dtype=np.float64),
        "cycles": _cycle_returns(index, config.cycles),
        "regime_shift": _regime_returns(config, rng),
        "jump_shocks": _jump_returns(config, rng),
    }
    component_returns["noise"] = (
        rng.normal(0.0, config.noise_std, config.rows) * volatility_multiplier
    )

    base_returns = sum(component_returns.values(), np.zeros(config.rows, dtype=np.float64))
    log_returns, mean_reversion_returns = _apply_mean_reversion(config, base_returns)
    component_returns["mean_reversion"] = mean_reversion_returns

    close = config.base_price * np.exp(np.cumsum(log_returns))
    open_price = _open_prices(config, close, rng)
    high, low, range_fraction = _high_low_prices(
        config=config,
        open_price=open_price,
        close=close,
        log_returns=log_returns,
        volatility_multiplier=volatility_multiplier,
        rng=rng,
    )
    volume = _volume(
        config=config,
        log_returns=log_returns,
        range_fraction=range_fraction,
        volatility_multiplier=volatility_multiplier,
        rng=rng,
    )
    typical_price = (open_price + high + low + close) / 4.0
    turnover = volume * typical_price
    timestamps = (
        config.start_timestamp + np.arange(config.rows, dtype=np.int64) * config.interval_ms
    )

    frame = pl.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_price.astype(np.float64),
            "high": high.astype(np.float64),
            "low": low.astype(np.float64),
            "close": close.astype(np.float64),
            "volume": volume.astype(np.float64),
            "turnover": turnover.astype(np.float64),
        }
    ).select(KLINE_COLUMNS)
    metadata = _metadata(
        config=config,
        frame=frame,
        log_returns=log_returns,
        component_returns=component_returns,
        volatility_multiplier=volatility_multiplier,
    )
    return frame, metadata


def _cycle_returns(index: np.ndarray, cycles: list[CycleComponent]) -> np.ndarray:
    returns = np.zeros(index.size, dtype=np.float64)
    rows = max(index.size - 1, 1)
    for cycle in cycles:
        phase = 2.0 * np.pi * index / cycle.period + cycle.phase
        wave = np.sin(phase) if cycle.kind == "sine" else np.cos(phase)
        envelope = np.exp(-cycle.decay * index / rows) if cycle.decay > 0.0 else 1.0
        returns += cycle.amplitude * wave * envelope
    return returns


def _regime_returns(config: SyntheticKlinesConfig, rng: np.random.Generator) -> np.ndarray:
    regime_config = config.regime_shift
    if not regime_config.enabled or regime_config.amplitude == 0.0:
        return np.zeros(config.rows, dtype=np.float64)

    levels = rng.choice([-1.0, 1.0], size=regime_config.count)
    levels *= rng.uniform(0.45, 1.0, size=regime_config.count) * regime_config.amplitude
    if regime_config.count == 1:
        return np.full(config.rows, levels[0], dtype=np.float64)

    index = np.arange(config.rows, dtype=np.float64)
    boundaries = np.linspace(0, config.rows - 1, regime_config.count + 1)[1:-1]
    regime = np.full(config.rows, levels[0], dtype=np.float64)
    for boundary, next_level in zip(boundaries, levels[1:], strict=True):
        blend = 0.5 * (1.0 + np.tanh((index - boundary) / regime_config.transition_steps))
        regime = regime * (1.0 - blend) + next_level * blend
    return regime


def _jump_returns(config: SyntheticKlinesConfig, rng: np.random.Generator) -> np.ndarray:
    jump_config = config.jump_shocks
    if not jump_config.enabled or jump_config.probability == 0.0 or jump_config.scale == 0.0:
        return np.zeros(config.rows, dtype=np.float64)
    mask = rng.random(config.rows) < jump_config.probability
    return rng.normal(0.0, jump_config.scale, config.rows) * mask


def _volatility_multiplier(
    config: SyntheticKlinesConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    cluster_config = config.volatility_cluster
    if not cluster_config.enabled or cluster_config.strength == 0.0:
        return np.ones(config.rows, dtype=np.float64)

    latent = np.zeros(config.rows, dtype=np.float64)
    innovations = rng.normal(0.0, 1.0, config.rows)
    innovation_scale = np.sqrt(max(1.0 - cluster_config.persistence**2, EPSILON))
    for index in range(1, config.rows):
        latent[index] = (
            cluster_config.persistence * latent[index - 1] + innovation_scale * innovations[index]
        )
    normalized = np.abs(latent) / max(float(np.std(latent)), EPSILON)
    return 1.0 + cluster_config.strength * normalized


def _apply_mean_reversion(
    config: SyntheticKlinesConfig,
    base_returns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    mean_config = config.mean_reversion
    if not mean_config.enabled or mean_config.strength == 0.0:
        return base_returns.copy(), np.zeros(config.rows, dtype=np.float64)

    log_level = np.zeros(config.rows, dtype=np.float64)
    base_log_price = np.log(config.base_price)
    log_returns = np.zeros(config.rows, dtype=np.float64)
    reversion = np.zeros(config.rows, dtype=np.float64)
    for index in range(config.rows):
        if index > 0:
            window_start = max(0, index - mean_config.window)
            rolling_mean = float(np.mean(log_level[window_start:index]))
            reversion[index] = -mean_config.strength * (log_level[index - 1] - rolling_mean)
        log_returns[index] = base_returns[index] + reversion[index]
        if index == 0:
            log_level[index] = base_log_price + log_returns[index]
        else:
            log_level[index] = log_level[index - 1] + log_returns[index]
    return log_returns, reversion


def _open_prices(
    config: SyntheticKlinesConfig,
    close: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    open_price = np.empty(config.rows, dtype=np.float64)
    gap_noise = rng.normal(0.0, config.gap_noise_std, config.rows)
    open_price[0] = config.base_price * np.exp(gap_noise[0])
    open_price[1:] = close[:-1] * np.exp(gap_noise[1:])
    return open_price


def _high_low_prices(
    config: SyntheticKlinesConfig,
    open_price: np.ndarray,
    close: np.ndarray,
    log_returns: np.ndarray,
    volatility_multiplier: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    body_high = np.maximum(open_price, close)
    body_low = np.minimum(open_price, close)
    candle_body = np.abs(np.log(np.maximum(close, EPSILON) / np.maximum(open_price, EPSILON)))
    baseline_range = config.noise_std * volatility_multiplier
    base_range = np.maximum(candle_body, baseline_range) * config.range_multiplier
    return_pressure = np.abs(log_returns) * 0.35
    wick_randomness = rng.uniform(0.25, 1.0, size=(2, config.rows))
    high_wick = config.wick_scale * (base_range + return_pressure) * wick_randomness[0]
    low_wick = config.wick_scale * (base_range + return_pressure) * wick_randomness[1]

    high = body_high * np.exp(high_wick)
    low = body_low * np.exp(-low_wick)
    range_fraction = np.log(np.maximum(high, EPSILON) / np.maximum(low, EPSILON))
    return high, low, range_fraction


def _volume(
    config: SyntheticKlinesConfig,
    log_returns: np.ndarray,
    range_fraction: np.ndarray,
    volatility_multiplier: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    return_scale = max(float(np.std(log_returns)), config.noise_std, EPSILON)
    range_scale = max(float(np.median(range_fraction)), config.noise_std, EPSILON)
    normalized_returns = np.abs(log_returns) / return_scale
    normalized_range = range_fraction / range_scale
    activity = (
        1.0
        + config.volume_return_sensitivity * normalized_returns
        + config.volume_range_sensitivity * normalized_range
        + config.volume_volatility_sensitivity * np.maximum(volatility_multiplier - 1.0, 0.0)
    )
    if config.volume_noise_std == 0.0:
        volume_noise = np.ones(config.rows, dtype=np.float64)
    else:
        volume_noise = rng.lognormal(
            mean=-0.5 * config.volume_noise_std**2,
            sigma=config.volume_noise_std,
            size=config.rows,
        )
    return config.base_volume * np.clip(activity, 0.05, None) * volume_noise


def _metadata(
    config: SyntheticKlinesConfig,
    frame: pl.DataFrame,
    log_returns: np.ndarray,
    component_returns: dict[str, np.ndarray],
    volatility_multiplier: np.ndarray,
) -> dict[str, object]:
    close = frame["close"].to_numpy().astype(np.float64)
    volume = frame["volume"].to_numpy().astype(np.float64)
    return {
        "schema": list(KLINE_COLUMNS),
        "config": config.model_dump(mode="json"),
        "seed": config.seed,
        "summary": {
            "rows": frame.height,
            "start_timestamp": int(frame["timestamp"][0]),
            "end_timestamp": int(frame["timestamp"][-1]),
            "interval_ms": config.interval_ms,
            "total_return": float(close[-1] / close[0] - 1.0),
            "log_return_mean": _safe_stat(log_returns, "mean"),
            "log_return_std": _safe_stat(log_returns, "std"),
            "price_drawdown_max": _max_drawdown(close),
            "close_min": float(np.min(close)),
            "close_max": float(np.max(close)),
            "volume_min": float(np.min(volume)),
            "volume_max": float(np.max(volume)),
        },
        "components": {
            "cycles": [cycle.model_dump(mode="json") for cycle in config.cycles],
            "returns": {name: _series_stats(values) for name, values in component_returns.items()},
            "volatility_multiplier": _series_stats(volatility_multiplier),
        },
    }


def _series_stats(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": _safe_stat(values, "mean"),
        "std": _safe_stat(values, "std"),
        "min": _safe_stat(values, "min"),
        "max": _safe_stat(values, "max"),
        "sum": _safe_stat(values, "sum"),
    }


def _safe_stat(values: np.ndarray, stat: str) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 0.0
    if stat == "std":
        return float(np.std(finite))
    if stat == "min":
        return float(np.min(finite))
    if stat == "max":
        return float(np.max(finite))
    if stat == "sum":
        return float(np.sum(finite))
    return float(np.mean(finite))


def _max_drawdown(values: np.ndarray) -> float:
    peaks = np.maximum.accumulate(values)
    drawdowns = 1.0 - values / np.maximum(peaks, EPSILON)
    return float(np.max(drawdowns))


def frame_to_records(frame: pl.DataFrame) -> list[dict[str, Any]]:
    return frame.select(KLINE_COLUMNS).to_dicts()
