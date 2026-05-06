import pytest

from synthetic_klines import CONFIG_CONTROL_PATHS, SyntheticKlinesConfig
from synthetic_klines.config import CycleComponent
from synthetic_klines.controls import control_schema, control_schema_payload


def test_config_rejects_extreme_linear_bias() -> None:
    with pytest.raises(ValueError, match="linear_bias"):
        SyntheticKlinesConfig(linear_bias=1.0)


def test_config_rejects_extreme_cycle_amplitude() -> None:
    with pytest.raises(ValueError, match="cycle amplitude"):
        SyntheticKlinesConfig(cycles=[CycleComponent(amplitude=1.0)])


def test_control_schema_covers_every_config_path_once() -> None:
    groups = control_schema()
    controls = [control for group in groups for control in group.controls]
    paths = [control.path for control in controls if not control.path.startswith("export.")]

    assert set(paths) == CONFIG_CONTROL_PATHS
    assert len(paths) == len(set(paths))
    assert control_schema_payload()[0]["key"] == "dataset_export"


def test_control_schema_has_hints_and_slider_or_non_slider_policy() -> None:
    for group in control_schema():
        assert group.key
        assert group.label
        assert group.controls
        for control in group.controls:
            assert control.label
            assert control.hint
            if control.input == "slider":
                assert control.min is not None
                assert control.max is not None
                assert control.step is not None
                assert control.non_slider_reason is None
            else:
                assert control.non_slider_reason


def test_control_schema_accepts_custom_defaults() -> None:
    groups = control_schema(SyntheticKlinesConfig(rows=123, seed=99))
    controls = {control.path: control for group in groups for control in group.controls}

    assert controls["rows"].default == 123
    assert controls["seed"].default == 99
