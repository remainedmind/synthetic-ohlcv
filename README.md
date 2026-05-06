# Synthetic Klines

Standalone synthetic OHLCV kline generator for learnable trading experiments.

Requires Python 3.11 or newer.

## Run The App

```bash
uv run synthetic-klines
```

Open `http://127.0.0.1:8100`.

Use a custom port when needed:

```bash
uv run synthetic-klines --port 8110
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

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Publish To pip

Build the package:

```bash
uv build
```

Recommended first publish to TestPyPI:

```bash
uv publish \
  --publish-url https://test.pypi.org/legacy/ \
  --check-url https://test.pypi.org/simple/ \
  --token "$TEST_PYPI_TOKEN"
```

Install-test from TestPyPI:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  synthetic-klines
```

Publish to PyPI:

```bash
uv publish --check-url https://pypi.org/simple/ --token "$PYPI_TOKEN"
```

After PyPI publish, users can install and run:

```bash
python -m pip install synthetic-klines
synthetic-klines
```
