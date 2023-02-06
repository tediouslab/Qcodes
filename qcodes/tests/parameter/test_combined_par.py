from collections import OrderedDict
from typing import Generator

import hypothesis.strategies as hst
import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from pytest_mock import MockerFixture

from qcodes.parameters import ManualParameter, combine
from qcodes.utils import full_class

from ..common import DumyPar


@pytest.fixture()
def parameters() -> Generator[list[ManualParameter], None, None]:
    parameters = [ManualParameter(name) for name in ["X", "Y", "Z"]]
    yield parameters


def testCombine(parameters: list[ManualParameter]) -> None:
    multipar = combine(*parameters, name="combined")
    assert multipar.dimensionality == len(parameters)


def testSweepBadSetpoints(parameters: list[ManualParameter]) -> None:
    with pytest.raises(ValueError):
        combine(*parameters, name="fail").sweep(np.array([[1, 2]]))


def testSweep(parameters: list[ManualParameter]) -> None:
    setpoints = np.array([[1, 1, 1], [1, 1, 1]])

    sweep_values = combine(*parameters, name="combined").sweep(setpoints)

    res = []
    for i in sweep_values:
        value = sweep_values.set(i)
        res.append([i, value])
    expected = [
            [0, [1, 1, 1]],
            [1, [1, 1, 1]]
            ]
    assert res == expected


def testSet(parameters: list[ManualParameter], mocker: MockerFixture) -> None:
    setpoints = np.array([[1, 1, 1], [1, 1, 1]])

    sweep_values = combine(*parameters, name="combined").sweep(setpoints)

    mock_method = mocker.patch.object(sweep_values, 'set')
    for i in sweep_values:
        sweep_values.set(i)

    mock_method.assert_has_calls([mocker.call(0), mocker.call(1)])  # pyright: ignore


@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
@given(
    npoints=hst.integers(1, 100),
    x_start_stop=hst.lists(hst.integers(), min_size=2, max_size=2).map(
        sorted  # type: ignore[arg-type]
    ),
    y_start_stop=hst.lists(hst.integers(), min_size=2, max_size=2).map(
        sorted  # type: ignore[arg-type]
    ),
    z_start_stop=hst.lists(hst.integers(), min_size=2, max_size=2).map(
        sorted  # type: ignore[arg-type]
    ),
)
def testAggregator(
    parameters: list[ManualParameter],
    npoints: int,
    x_start_stop: list[int],
    y_start_stop: list[int],
    z_start_stop: list[int],
) -> None:
    x_set = np.linspace(x_start_stop[0], x_start_stop[1], npoints).reshape(npoints, 1)
    y_set = np.linspace(y_start_stop[0], y_start_stop[1], npoints).reshape(npoints, 1)
    z_set = np.linspace(z_start_stop[0], z_start_stop[1], npoints).reshape(npoints, 1)
    setpoints = np.hstack((x_set, y_set, z_set))
    expected_results = [linear(*set) for set in setpoints]
    sweep_values = combine(*parameters,
                           name="combined",
                           aggregator=linear).sweep(setpoints)

    results = []
    for i, value in enumerate(sweep_values):
            res = sweep_values.set(value)
            results.append(sweep_values._aggregate(*res))

    assert results == expected_results


def testMeta(parameters: list[ManualParameter]) -> None:
    name = "combined"
    label = "Linear Combination"
    unit = "a.u"
    aggregator = linear
    sweep_values = combine(*parameters,
                           name=name,
                           label=label,
                           unit=unit,
                           aggregator=aggregator
                           )
    snap = sweep_values.snapshot()
    out = OrderedDict()
    out['__class__'] = full_class(sweep_values)
    out["unit"] = unit
    out["label"] = label
    out["full_name"] = name
    out["aggregator"] = repr(linear)
    for param in sweep_values.parameters:
        out[param.full_name] = {}  # type: ignore[assignment]
    assert out == snap


def testMutable(parameters: list[ManualParameter]) -> None:
    setpoints = np.array([[1, 1, 1], [1, 1, 1]])

    sweep_values = combine(*parameters,
                           name="combined")
    a = sweep_values.sweep(setpoints)
    setpoints = np.array([[2, 1, 1], [1, 1, 1]])
    b = sweep_values.sweep(setpoints)
    assert a != b


def testArrays(parameters: list[ManualParameter]) -> None:
    x_vals = np.linspace(1, 1, 2)
    y_vals = np.linspace(1, 1, 2)
    z_vals = np.linspace(1, 1, 2)
    sweep_values = combine(*parameters,
                           name="combined").sweep(x_vals, y_vals, z_vals)
    res = []
    for i in sweep_values:
        value = sweep_values.set(i)
        res.append([i, value])

    expected = [
            [0, [1, 1, 1]],
            [1, [1, 1, 1]]
            ]
    assert res == expected


def testWrongLen(parameters: list[ManualParameter]) -> None:
    x_vals = np.linspace(1, 1, 2)
    y_vals = np.linspace(1, 1, 2)
    z_vals = np.linspace(1, 1, 3)
    with pytest.raises(ValueError):
        combine(*parameters,
                name="combined").sweep(x_vals, y_vals, z_vals)


def testInvalidName(parameters: list[ManualParameter]) -> None:
    x_vals = np.linspace(1, 1, 2)
    y_vals = np.linspace(1, 1, 2)
    z_vals = np.linspace(1, 1, 2)
    with pytest.raises(ValueError):
        combine(*parameters,
                name="combined with spaces").sweep(x_vals, y_vals, z_vals)


def testLen(parameters: list[ManualParameter]) -> None:
    x_vals = np.linspace(1, 1, 2)
    y_vals = np.linspace(1, 1, 2)
    z_vals = np.linspace(1, 0, 2)
    sweep_values = combine(*parameters,
                           name="combined").sweep(x_vals, y_vals, z_vals)
    assert len(x_vals) == len(sweep_values.setpoints)


def linear(x: float, y: float, z: float) -> float:
    return x+y+z
