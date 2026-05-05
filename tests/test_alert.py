"""Tests for AlertRule, AlertManager, and AlertStream."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from geofence_watch.alert import AlertManager, AlertRule
from geofence_watch.alert_stream import AlertStream
from geofence_watch.checker import GeofenceChecker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.fence import Geofence
from geofence_watch.point import Point

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQUARE = {
    "type": "Feature",
    "properties": {"name": "zone_a"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]],
    },
}


@pytest.fixture()
def checker() -> GeofenceChecker:
    c = GeofenceChecker()
    c.register(Geofence.from_geojson(SQUARE))
    return c


@pytest.fixture()
def manager() -> AlertManager:
    return AlertManager()


@pytest.fixture()
def alert_stream(checker: GeofenceChecker) -> AlertStream:
    return AlertStream(checker)


def _make_event(event_type: EventType, fence: str = "zone_a", obj: str = "car1") -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj,
        fence_name=fence,
        event_type=event_type,
        point=Point(lon=1.0, lat=1.0),
    )


# ---------------------------------------------------------------------------
# AlertRule.matches
# ---------------------------------------------------------------------------

class TestAlertRuleMatches:
    def _rule(self, event_type=EventType.ENTER, object_id=None):
        return AlertRule(
            name="r1",
            fence_name="zone_a",
            event_type=event_type,
            callback=MagicMock(),
            object_id=object_id,
        )

    def test_matches_correct_event(self):
        rule = self._rule()
        assert rule.matches(_make_event(EventType.ENTER))

    def test_no_match_wrong_fence(self):
        rule = self._rule()
        assert not rule.matches(_make_event(EventType.ENTER, fence="other"))

    def test_no_match_wrong_event_type(self):
        rule = self._rule()
        assert not rule.matches(_make_event(EventType.EXIT))

    def test_matches_specific_object(self):
        rule = self._rule(object_id="car1")
        assert rule.matches(_make_event(EventType.ENTER, obj="car1"))

    def test_no_match_wrong_object(self):
        rule = self._rule(object_id="car1")
        assert not rule.matches(_make_event(EventType.ENTER, obj="bus9"))


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

def test_add_and_count(manager):
    cb = MagicMock()
    manager.add_rule(AlertRule("r1", "zone_a", EventType.ENTER, cb))
    assert len(manager) == 1
    assert "r1" in manager.rule_names


def test_duplicate_rule_raises(manager):
    cb = MagicMock()
    manager.add_rule(AlertRule("r1", "zone_a", EventType.ENTER, cb))
    with pytest.raises(ValueError):
        manager.add_rule(AlertRule("r1", "zone_a", EventType.EXIT, cb))


def test_remove_rule(manager):
    cb = MagicMock()
    manager.add_rule(AlertRule("r1", "zone_a", EventType.ENTER, cb))
    manager.remove_rule("r1")
    assert len(manager) == 0


def test_remove_missing_rule_raises(manager):
    with pytest.raises(KeyError):
        manager.remove_rule("ghost")


def test_evaluate_fires_callback(manager):
    cb = MagicMock()
    manager.add_rule(AlertRule("r1", "zone_a", EventType.ENTER, cb))
    event = _make_event(EventType.ENTER)
    fired = manager.evaluate(event)
    assert fired == 1
    cb.assert_called_once_with(event)


def test_evaluate_no_match(manager):
    cb = MagicMock()
    manager.add_rule(AlertRule("r1", "zone_a", EventType.ENTER, cb))
    fired = manager.evaluate(_make_event(EventType.EXIT))
    assert fired == 0
    cb.assert_not_called()


# ---------------------------------------------------------------------------
# AlertStream integration
# ---------------------------------------------------------------------------

def test_alert_stream_fires_on_enter(alert_stream):
    cb = MagicMock()
    alert_stream.add_rule(AlertRule("enter_alert", "zone_a", EventType.ENTER, cb))
    inside = Point(lon=1.0, lat=1.0)
    events = alert_stream.process("obj1", inside)
    assert any(e.event_type == EventType.ENTER for e in events)
    cb.assert_called_once()


def test_alert_stream_no_fire_when_already_inside(alert_stream):
    cb = MagicMock()
    alert_stream.add_rule(AlertRule("enter_alert", "zone_a", EventType.ENTER, cb))
    inside = Point(lon=1.0, lat=1.0)
    alert_stream.process("obj1", inside)
    cb.reset_mock()
    alert_stream.process("obj1", inside)  # still inside, no new ENTER
    cb.assert_not_called()


def test_alert_stream_exit_fires_callback(alert_stream):
    cb = MagicMock()
    alert_stream.add_rule(AlertRule("exit_alert", "zone_a", EventType.EXIT, cb))
    inside = Point(lon=1.0, lat=1.0)
    outside = Point(lon=5.0, lat=5.0)
    alert_stream.process("obj1", inside)
    alert_stream.process("obj1", outside)
    cb.assert_called_once()
