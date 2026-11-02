"""Pure cursor commands and visible views; clock supplied by the caller."""
import math
import pandas as pd
from c_dashboard.data.schema import TARGET_UNITS
from c_dashboard.replay.temporal import IDENTIFIERS
from c_dashboard.replay.types import VisibilitySnapshot


def token(state):
    return (state.lifecycle_token, state.stream_id, state.generation, state.cursor, state.virtual_clock)


def content_token(state):
    """Navigation epochs reject requests but do not change visible content."""
    return (state.stream_id, state.generation, state.cursor, state.virtual_clock)


def restart(state):
    state.generation += 1
    state.cursor, state.playing, state.virtual_clock = 0, False, None
    state.last_tick, state.last_tick_sequence = None, -1
    state.spc_events.clear()
    state.spc_processed_cursor = 0


def command(state, timeline, action, now, *, speed=None):
    if action == "restart":
        restart(state)
    elif action == "pause":
        state.playing, state.last_tick = False, None
    elif action == "step":
        state.playing, state.last_tick = False, None
        state.cursor = min(len(timeline.groups), state.cursor + 1)
        if state.cursor:
            state.virtual_clock = timeline.groups[state.cursor - 1][0].available_at.isoformat()
    elif action == "play":
        if state.cursor < len(timeline.groups) and not state.playing:
            state.playing, state.last_tick = True, now
            state.last_tick_sequence = -1
            if state.virtual_clock is None:
                state.virtual_clock = timeline.groups[0][0].available_at.isoformat()
    elif action == "speed":
        if speed not in (.5, 1., 2., 4.):
            raise ValueError("不支援的回放倍率")
        state.speed = speed
        state.last_tick = now if state.playing else None
        state.last_tick_sequence = -1
    else:
        raise ValueError("未知回放操作")


def tick(state, timeline, now, expected_generation, *, lifecycle_token="workspace"):
    if (not state.playing or state.last_tick is None or expected_generation != state.generation
            or lifecycle_token != state.lifecycle_token):
        return False
    # At most one notification per 250 ms monotonic slot; normal UI reruns do not consume it twice.
    sequence = math.floor(now * 4)
    if sequence <= state.last_tick_sequence or now <= state.last_tick:
        return False
    elapsed = now - state.last_tick
    state.last_tick, state.last_tick_sequence = now, sequence
    clock = pd.Timestamp(state.virtual_clock) + pd.Timedelta(seconds=elapsed * state.speed)
    while state.cursor < len(timeline.groups) and timeline.groups[state.cursor][0].available_at <= clock:
        state.cursor += 1
    if state.cursor == len(timeline.groups):
        state.playing = False
        clock = timeline.groups[-1][0].available_at
    state.virtual_clock = clock.isoformat()
    return True


def visibility(state, timeline):
    events = [e for g in timeline.groups[:state.cursor] for e in g]
    released = frozenset((e.source_row, e.field) for e in events)
    ids = {n for n, f in released if f == "__identity__"}
    rows = timeline.frame.loc[timeline.frame.source_row.isin(ids)].copy() if "source_row" in timeline.frame else timeline.frame.copy()
    for name in rows:
        if name not in IDENTIFIERS:
            mask = rows.source_row.map(lambda n: (int(n), name) in released)
            rows[name] = rows[name].where(mask)
    identity_times = {e.source_row: e.available_at for e in events if e.field == "__identity__"}
    if "source_row" in rows:
        rows["available_at"] = pd.Series([identity_times[int(n)] for n in rows.source_row], index=rows.index,
                                         dtype="datetime64[ns, Asia/Taipei]")
    # Global loader duplicate flags can depend on future specimens. Re-evaluate
    # only explicit currently known specimen keys, without comparing hidden values.
    if "specimen_id" in rows:
        has_id = rows.specimen_id.fillna("").ne("")
        duplicate = has_id & rows.duplicated(["product_batch", "specimen_id"], keep=False)
    else:
        duplicate = pd.Series(False, index=rows.index)
    rows["duplicate_record"] = duplicate
    if "timestamp" in rows and "product_batch" in rows:
        rows["identity_valid"] = rows.timestamp.notna() & rows.product_batch.fillna("").ne("") & ~duplicate
    # No unreleased raw or metadata columns bypass the channel projection.
    raw = timeline.raw.loc[timeline.raw.index.isin(ids)].copy()
    for name in raw:
        raw[name] = raw[name].where([name in IDENTIFIERS or (int(n), name) in released for n in raw.index])
    measurements = {}
    for target in TARGET_UNITS:
        view = rows.copy()
        es = {e.source_row: e for e in events if e.field == target}
        for other in TARGET_UNITS:
            if other != target and other in view:
                view[other] = float("nan")
        if target in view:
            # Keep missing specimens as barriers; never drop them to fabricate a valid subgroup.
            for idx, r in view.iterrows():
                e = es.get(int(r.source_row))
                if e:
                    view.at[idx, "timestamp"] = e.occurred_at
                    view.at[idx, "available_at"] = e.available_at
        measurements[target] = view
    rows.attrs["replay_token"] = token(state)
    cutoff = state.virtual_clock if state.cursor else None
    reasons = timeline.reasons if timeline.profile is None else tuple(
        message for n, f, known, message in timeline.diagnostics
        if n in ids and (known is None or (cutoff and pd.Timestamp(known) <= pd.Timestamp(cutoff))))
    return VisibilitySnapshot(token(state), cutoff, rows, raw, measurements, released,
                              len(ids), len(timeline.frame), state.cursor, len(timeline.groups), reasons)
