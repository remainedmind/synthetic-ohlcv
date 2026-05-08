# Synthetic Klines

`synthetic-ohlcv` is a Python synthetic OHLCV data generator for controlled trading ML
experiments, time-series pipeline tests, and reproducible market-like candlestick data. It
generates synthetic kline datasets with valid `open`, `high`, `low`, `close`, `volume`, and
`turnover` columns, returns data as a Polars `DataFrame`, and includes a local FastAPI and Plotly
preview app for interactive scenario design.

The package is designed for experiments where you want to know whether a model, feature pipeline,
or backtest harness can recover a known synthetic signal. It is not intended to prove that a
strategy will work on real exchange data.

## Features

- Generate reproducible synthetic OHLCV and kline data with a fixed random seed.
- Create valid candlestick data with ordered timestamps and coherent high/low/open/close values.
- Tune learnable components such as trend bias, cyclic returns, return noise, candle gaps, wicks,
  volume response, regime shifts, volatility clustering, jump shocks, and mean reversion.
- Export datasets to Parquet, CSV, and JSON metadata.
- Use a small Python API for notebooks, scripts, tests, and ML experiments.
- Run a local FastAPI app with Plotly candlestick and volume charts for visual inspection.

## Installation

Install from PyPI with `pip`:

```bash
python -m pip install synthetic-ohlcv
```

Or install with `uv`:

```bash
uv pip install synthetic-ohlcv
```

Requires Python 3.11 or newer.

## Quickstart

```python
from synthetic_ohlcv import SyntheticKlinesConfig, make_synthetic_ohlcv

config = SyntheticKlinesConfig(rows=4_000, seed=43)
frame = make_synthetic_ohlcv(config)

print(frame.head())
```

The returned object is a Polars `DataFrame`, so it can be written, filtered, converted, or joined
with normal Polars APIs.

## Dataset Schema

Generated datasets contain exactly these columns:

| Column | Meaning |
| --- | --- |
| `timestamp` | Candle open timestamp in milliseconds. |
| `open` | Candle open price. |
| `high` | Candle high price. |
| `low` | Candle low price. |
| `close` | Candle close price. |
| `volume` | Synthetic traded volume. |
| `turnover` | Synthetic traded value, computed from volume and typical candle price. |

## Run The Preview App

After installation, run:

```bash
synthetic-ohlcv
```

Open `http://127.0.0.1:8100`.

For local development, you can also run:

```bash
uv run synthetic-ohlcv
```

Use a custom host or port when needed:

```bash
synthetic-ohlcv --host 127.0.0.1 --port 8110
uv run synthetic-ohlcv --port 8110
```

The app lets you adjust generation controls, preview synthetic candlestick and volume charts, and
save the resulting dataset.

## Python Examples

### Reproducible Data

Use the same configuration and seed to generate the same dataset again.

```python
from synthetic_ohlcv import SyntheticKlinesConfig, make_synthetic_ohlcv

config = SyntheticKlinesConfig(rows=1_000, seed=123)

left = make_synthetic_ohlcv(config)
right = make_synthetic_ohlcv(config)

assert left.equals(right)
```

### Save Parquet, CSV, And Metadata

```python
from synthetic_ohlcv import SyntheticKlinesConfig, save_synthetic_ohlcv

result = save_synthetic_ohlcv(
    config=SyntheticKlinesConfig(rows=5_000, seed=7),
    dataset_name="cycle_debug_run",
    output_dir="exports",
)

print(result.parquet_path)
print(result.csv_path)
print(result.metadata_path)
```

This writes:

```text
exports/cycle_debug_run.parquet
exports/cycle_debug_run.csv
exports/cycle_debug_run.metadata.json
```

### Inspect Generation Metadata

Use metadata to understand the generated scenario and summarize the synthetic components.

```python
from synthetic_ohlcv import SyntheticKlinesConfig, make_synthetic_ohlcv_with_metadata

frame, metadata = make_synthetic_ohlcv_with_metadata(
    SyntheticKlinesConfig(rows=2_000, seed=21)
)

print(metadata["summary"]["total_return"])
print(metadata["components"]["returns"]["cycles"])
```

Metadata is useful for diagnostics and experiment tracking. Do not feed it into a model unless you
are intentionally building a supervised synthetic task with known generation labels.

### Flat Null Benchmark

Start with a flat dataset when validating that a training loop, feature store, or backtest harness
does not invent signal where no signal exists.

```python
from synthetic_ohlcv import (
    JumpShockConfig,
    MeanReversionConfig,
    RegimeShiftConfig,
    SyntheticKlinesConfig,
    VolatilityClusterConfig,
    make_synthetic_ohlcv,
)

config = SyntheticKlinesConfig(
    rows=1_000,
    base_price=500.0,
    linear_bias=0.0,
    noise_std=0.0,
    gap_noise_std=0.0,
    wick_scale=0.0,
    range_multiplier=0.0,
    volume_noise_std=0.0,
    volume_return_sensitivity=0.0,
    volume_range_sensitivity=0.0,
    volume_volatility_sensitivity=0.0,
    cycles=[],
    regime_shift=RegimeShiftConfig(enabled=False, amplitude=0.0),
    volatility_cluster=VolatilityClusterConfig(enabled=False, strength=0.0),
    jump_shocks=JumpShockConfig(enabled=False, probability=0.0, scale=0.0),
    mean_reversion=MeanReversionConfig(enabled=False, strength=0.0),
)

frame = make_synthetic_ohlcv(config)
```

### Harder Market-Like Scenario

Combine multiple components to create a less stationary synthetic benchmark.

```python
from synthetic_ohlcv import (
    CycleComponent,
    JumpShockConfig,
    MeanReversionConfig,
    RegimeShiftConfig,
    SyntheticKlinesConfig,
    VolatilityClusterConfig,
    make_synthetic_ohlcv_with_metadata,
)

config = SyntheticKlinesConfig(
    rows=10_000,
    seed=99,
    cycles=[
        CycleComponent(kind="sine", amplitude=0.0010, period=96),
        CycleComponent(kind="cosine", amplitude=0.0007, period=672, phase=0.5, decay=0.2),
    ],
    regime_shift=RegimeShiftConfig(enabled=True, count=4, amplitude=0.0002),
    volatility_cluster=VolatilityClusterConfig(enabled=True, strength=0.5),
    jump_shocks=JumpShockConfig(enabled=True, probability=0.01, scale=0.003),
    mean_reversion=MeanReversionConfig(enabled=True, strength=0.01, window=72),
)

frame, metadata = make_synthetic_ohlcv_with_metadata(config)
```

## Guidance For ML Experiments

- Start with a flat null benchmark, then move to an easy cyclic scenario, then add noise,
  nonstationarity, jumps, and volatility clustering.
- Keep the seed fixed while debugging feature engineering, data loading, and model training.
- Change seeds and scenario parameters when checking robustness.
- Split by timestamp, not by shuffled rows, to avoid time-series leakage.
- Use the same scenario across models when comparing architecture or feature changes.
- Track the JSON metadata next to model runs so you can explain which synthetic signals were
  present.
- Treat synthetic results as controlled evidence about your pipeline or model behavior, not as
  evidence of live trading profitability.

## When To Use This

`synthetic-ohlcv` is useful for:

- ML pipeline smoke tests with realistic OHLCV-shaped data.
- Signal-recovery experiments where the target pattern is intentionally generated.
- Overfitting and leakage diagnostics.
- Backtest and data-loader fixtures.
- Notebook examples that should not depend on external exchange APIs.
- Reproducible benchmarks for feature engineering and model iteration.

## Limitations

Synthetic candles are not real markets. This package does not simulate an order book, bid/ask
spread, exchange latency, slippage, liquidation cascades, market impact, cross-asset correlation,
or real participant behavior. Use real exchange data and realistic execution assumptions before
drawing conclusions about trading performance.

## Development

Install development dependencies with `uv`, then run the tests:

```bash
uv sync
uv run pytest
```

The test suite verifies schema invariants, reproducibility, export behavior, FastAPI routes, and
the configured coverage gate.
