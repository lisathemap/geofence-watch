"""Tests for EntryCounter and EntryStream."""

from __future__ import annotations

import pytest

from geofence_watch.entry_counter import EntryCounter, EntryKey
from geofence_watch.entry_stream import EntryStream
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


def _make_event(
    event_type: EventType,
    object_id: str = "obj-1",
    fence_name: str = "zone-a",
) -> GeofenceEvent:
    return GeofenceEvent(
        event_type=event_type,
        object_id=object_id,
        fence_name=fence_name,
        point=Point(lon=0.0, lat=0.0),
        timestamp=1_000_000.0,
    )


# ---------------------------------------------------------------------------
# EntryCounter init
# ---------------------------------------------------------------------------

class TestEntryCounterInit:
    def test_default_track_objects_is_none(self):
        ec = EntryCounter()
        assert ec.track_objects is None

    def test_default_track_fences_is_none(self):
        ec = EntryCounter()
        assert ec.track_fences is None

    def test_custom_track_objects_stored_as_tuple(self):
        ec = EntryCounter(track_objects=["a", "b"])
        assert ec.track_objects == ("a", "b")

    def test_custom_track_fences_stored_as_tuple(self):
        ec = EntryCounter(track_fences=["zone-a"])
        assert ec.track_fences == ("zone-a",)

    def test_count_unknown_pair_is_zero(self):
        ec = EntryCounter()
        assert ec.count("x", "y") == 0

    def test_total_starts_at_zero(self):
        ec = EntryCounter()
        assert ec.total() == 0


# ---------------------------------------------------------------------------
# EntryCounter ingest
# ---------------------------------------------------------------------------

class TestEntryCounterIngest:
    def test_enter_increments_count(self):
        ec = EntryCounter()
        ec.ingest(_make_event(EventType.ENTER))
        assert ec.count("obj-1", "zone-a") == 1

    def test_exit_does_not_increment(self):
        ec = EntryCounter()
        ec.ingest(_make_event(EventType.EXIT))
        assert ec.count("obj-1", "zone-a") == 0

    def test_multiple_enters_accumulate(self):
        ec = EntryCounter()
        for _ in range(3):
            ec.ingest(_make_event(EventType.ENTER))
        assert ec.count("obj-1", "zone-a") == 3

    def test_total_sums_all_pairs(self):
        ec = EntryCounter()
        ec.ingest(_make_event(EventType.ENTER, object_id="a", fence_name="f1"))
        ec.ingest(_make_event(EventType.ENTER, object_id="b", fence_name="f2"))
        assert ec.total() == 2

    def test_track_objects_filter_blocks_other(self):
        ec = EntryCounter(track_objects=("allowed",))
        ec.ingest(_make_event(EventType.ENTER, object_id="blocked"))
        assert ec.total() == 0

    def test_track_fences_filter_blocks_other(self):
        ec = EntryCounter(track_fences=("zone-a",))
        ec.ingest(_make_event(EventType.ENTER, fence_name="zone-b"))
        assert ec.total() == 0

    def test_callback_called_on_enter(self):
        results = []
        ec = EntryCounter()
        ec.add_callback("cb", lambda key, cnt: results.append((key, cnt)))
        ec.ingest(_make_event(EventType.ENTER))
        assert len(results) == 1
        key, cnt = results[0]
        assert key == EntryKey("obj-1", "zone-a")
        assert cnt == 1

    def test_callback_not_called_on_exit(self):
        results = []
        ec = EntryCounter()
        ec.add_callback("cb", lambda key, cnt: results.append(cnt))
        ec.ingest(_make_event(EventType.EXIT))
        assert results == []

    def test_remove_callback_stops_calls(self):
        results = []
        ec = EntryCounter()
        ec.add_callback("cb", lambda key, cnt: results.append(cnt))
        ec.remove_callback("cb")
        ec.ingest(_make_event(EventType.ENTER))
        assert results == []

    def test_reset_clears_counts(self):
        ec = EntryCounter()
        ec.ingest(_make_event(EventType.ENTER))
        ec.reset()
        assert ec.total() == 0

    def test_add_non_callable_raises(self):
        ec = EntryCounter()
        with pytest.raises(TypeError):
            ec.add_callback("bad", "not-callable")  # type: ignore


# ---------------------------------------------------------------------------
# EntryStream
# ---------------------------------------------------------------------------

class TestEntryStream:
    def test_default_counter_created(self):
        es = EntryStream()
        assert isinstance(es.counter, EntryCounter)

    def test_custom_counter_accepted(self):
        ec = EntryCounter()
        es = EntryStream(counter=ec)
        assert es.counter is ec

    def test_invalid_counter_raises(self):
        with pytest.raises(TypeError):
            EntryStream(counter="bad")  # type: ignore

    def test_process_enter_increments(self):
        es = EntryStream()
        es.process(_make_event(EventType.ENTER))
        assert es.count("obj-1", "zone-a") == 1

    def test_process_non_event_raises(self):
        es = EntryStream()
        with pytest.raises(TypeError):
            es.process("not-an-event")  # type: ignore

    def test_total_delegates_to_counter(self):
        es = EntryStream()
        es.process(_make_event(EventType.ENTER))
        assert es.total() == 1

    def test_reset_delegates_to_counter(self):
        es = EntryStream()
        es.process(_make_event(EventType.ENTER))
        es.reset()
        assert es.total() == 0
