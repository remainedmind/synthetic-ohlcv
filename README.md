# Synthetic Klines

Standalone synthetic OHLCV kline generator for learnable trading experiments.

Requires Python 3.11 or newer.

## Installation

Install from PyPI with `pip`:

```bash
python -m pip install synthetic-ohlcv
```

Or install with `uv`:

```bash
uv pip install synthetic-ohlcv
```

## Run The App

After installation, run:

```bash
synthetic-ohlcv
```

Open `http://127.0.0.1:8100`.

For local development, you can also run:

```bash
uv run synthetic-ohlcv
```

Use a custom port when needed:

```bash
uv run synthetic-ohlcv --port 8110
```

## Python API

```python
from synthetic_ohlcv import SyntheticKlinesConfig, make_synthetic_ohlcv

frame = make_synthetic_ohlcv(SyntheticKlinesConfig(rows=4_000, seed=43))
```

Generated datasets contain exactly:

```text
timestamp, open, high, low, close, volume, turnover
```
