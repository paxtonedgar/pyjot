import math

import pytest

import jot
from jot import facade, util
from jot.base import Meter, Span, Target
from jot.fanout import FanOutTarget
from jot.sampling import SamplingTarget


@pytest.fixture
def target():
    return Target()


def test_ratio_one_forwards_finish(target, mocker):
    finish = mocker.spy(target, "finish")
    sampler = SamplingTarget(target, 1.0)
    for _ in range(100):
        sampler.finish({}, Span())
    assert finish.call_count == 100


def test_ratio_zero_drops_finish(target, mocker):
    finish = mocker.spy(target, "finish")
    sampler = SamplingTarget(target, 0.0)
    for _ in range(100):
        sampler.finish({}, Span())
    finish.assert_not_called()


@pytest.mark.parametrize(
    "method_name, args",
    [
        ("event", ("an event",)),
        ("log", (jot.log.WARNING, "a message")),
        ("error", ("an error", RuntimeError("boom"))),
        ("magnitude", ("a magnitude", 1.5)),
        ("count", ("a count", 3)),
    ],
)
def test_ratio_zero_forwards_everything_else(target, mocker, method_name, args):
    method = mocker.spy(target, method_name)
    sampler = SamplingTarget(target, 0.0)
    tags = {"flooge": 91}
    span = Span()
    getattr(sampler, method_name)(*args, tags, span)
    method.assert_called_once_with(*args, tags, span)


def test_accepts_log_level_delegates():
    sampler = SamplingTarget(Target(jot.log.WARNING), 0.5)
    assert sampler.accepts_log_level(jot.log.WARNING)
    assert not sampler.accepts_log_level(jot.log.INFO)


def test_decision_is_shared_within_a_trace(target, mocker):
    finish = mocker.spy(target, "finish")
    sampler = SamplingTarget(target, 0.5)
    for _ in range(100):
        parent = Meter(sampler).start("parent")
        child = parent.start("child")
        child.finish()
        parent.finish()
        assert finish.call_count % 2 == 0

    # same trace id, same decision, every time
    span = Span()
    decisions = set()
    for _ in range(10):
        before = finish.call_count
        sampler.finish({}, Span(trace_id=span.trace_id))
        decisions.add(finish.call_count > before)
    assert len(decisions) == 1


def test_sample_rate(target, mocker):
    finish = mocker.spy(target, "finish")
    sampler = SamplingTarget(target, 0.25)
    util.init_random(1234)
    try:
        for _ in range(10_000):
            sampler.finish({}, Span())
    finally:
        util.init_random()

    # binomial standard deviation is sqrt(0.25 * 0.75 / 10000) ~= 0.0043, so 0.02 is over 4.5
    # standard deviations; the seed makes the outcome deterministic regardless
    assert abs(finish.call_count / 10_000 - 0.25) < 0.02


@pytest.mark.parametrize("ratio", [-0.1, 1.1, math.nan])
def test_invalid_ratio(target, ratio):
    with pytest.raises(ValueError):
        SamplingTarget(target, ratio)


def test_wraps_fanout(mocker):
    zero = Target()
    one = Target()
    zero_finish = mocker.spy(zero, "finish")
    one_finish = mocker.spy(one, "finish")
    one_count = mocker.spy(one, "count")

    sampler = SamplingTarget(FanOutTarget(zero, one), 0.0)
    sampler.finish({}, Span())
    sampler.count("a count", 1, {}, None)

    zero_finish.assert_not_called()
    one_finish.assert_not_called()
    one_count.assert_called_once()


@pytest.fixture
def reset_env(monkeypatch):
    monkeypatch.delenv("JOT_TRACE_SAMPLE_RATE", raising=False)
    monkeypatch.delenv("TRACE_SAMPLE_RATE", raising=False)
    original_meter = facade.active_meter
    yield
    facade.active_meter = original_meter


def test_env_wraps_target(reset_env, monkeypatch):
    monkeypatch.setenv("JOT_TRACE_SAMPLE_RATE", "0.5")
    jot.init_from_environment()
    assert isinstance(facade.active_meter.target, SamplingTarget)


def test_env_unset_leaves_target_unwrapped(reset_env):
    jot.init_from_environment()
    assert not isinstance(facade.active_meter.target, SamplingTarget)


@pytest.mark.parametrize("rate", ["garbage", "1.5", "nan"])
def test_env_invalid_rate(reset_env, monkeypatch, rate):
    monkeypatch.setenv("JOT_TRACE_SAMPLE_RATE", rate)
    with pytest.raises(ValueError, match="TRACE_SAMPLE_RATE"):
        jot.init_from_environment()
