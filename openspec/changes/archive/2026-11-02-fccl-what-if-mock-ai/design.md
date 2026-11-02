# Design

## Context

See [proposal.md](proposal.md) for the change motivation and scope. The C1–C3 implementation already has `ModelAdapter`／`PredictionInput`／`PredictionResult` ports in `c_dashboard/adapters/base.py`, an `UnavailableAdapter`, a `WorkspaceState` containing `WhatIfState` and immutable `SegmentSnapshot`, one What-if Tab, and a top-level Alarm area that currently renders SPC events only. `selected_rows` and the SPC service operate on explicit data slices; the existing SPC result is computed once and shared between its panel and overview. No prediction, recommendation, or What-if calculation is implemented yet.

## Goals / Non-Goals

**Goals:**

- Add deterministic, pure prediction and recommendation paths that can be tested independently of Streamlit.
- Preserve fixed comparison identity and isolate candidate parameters/results from measured rows, SPC inputs, and SPC state.
- Render prediction state and alarms beside SPC alarms while keeping their source, decision rules, and identifiers separate.
- Make the C Mock replaceable through the existing adapter boundary without requiring B to use C's formulas or internal types.

**Non-Goals:**

- No Random Forest training, SHAP/Heatmap rendering, CSV replay, formal A/B adapter, PLC/MES write, or plant-control action.
- No decision of official quality limits, appearance risk threshold, or formal multi-objective recommendation policy; TCP-004 remains pending handoff.

## Decisions

### D1. Keep the adapter boundary and add a versioned C formula implementation

Implement a C-only formula adapter under `c_dashboard/adapters/` against the existing prediction port, expanding the internal result shape only where needed to report capabilities, unavailable targets, units, and demo-risk semantics. The adapter is deterministic and stateless: its output depends only on its explicit features, formula version, and mock configuration. It accepts process/environment features and an identifier, never measured quality targets, hidden fixture truth, replay-future rows, or SPC results. It returns four numeric target estimates plus an appearance prediction and clearly uncalibrated demo-risk value when supported.

This preserves a replaceable boundary while keeping B's artifact, preprocessing, feature order, and SHAP contract open for C9. A separate duplicate prediction stack or adapting B's training code into C was considered and rejected because either couples the dashboard to implementation details or duplicates B's responsibility.

### D2. Freeze one immutable comparison context, keep candidates as a delta

When data is available, initialize What-if to the latest visible material segment. On the first user edit, retain its source, batch, material segment, timestamp, original process settings, and environment in `SegmentSnapshot`; create a separate candidate map containing only explicitly changed allowlisted parameters. A user reselecting an already available segment creates a new snapshot and invalidates prior candidate predictions and recommendations. CSV rows and `SpcResult` remain read-only inputs and are never populated with predictions.

Keep durable business state in `WorkspaceState.what_if`, with widget keys as UI state only. Existing session initialization/source-reset handling remains the owner of lifecycle boundaries; add focused reset logic for changing the selected comparison segment. This follows the current mutable workspace container and immutable snapshot pattern instead of using widget values as the only source of truth.

### D3. Separate prediction, risk decisions, and recommendation policy

Use small pure services/configuration objects under a C-internal quality or what-if package:

1. A prediction service maps the fixed snapshot and candidate parameters to adapter inputs, validates output identity/shape/units, and returns before/after records.
2. A test-rule configuration contains illustrative acceptance bounds and appearance-risk threshold with explicit source/version. Values are supplied by C test configuration, not hidden constants or TCP-004 assumptions. Missing/unavailable limits produce an indeterminate outcome rather than pass.
3. A recommendation strategy evaluates a configured candidate set and emits the selected candidate's actual parameter delta, unit, predicted changes, strategy version, and rationale, or a typed no-recommendation reason. The demonstration scenarios cover improvement, worsening, no candidate, and insufficient information, including a configured −0.2 m/min example. The strategy is replaceable and makes no claim about official multi-objective trade-offs.

Combining prediction, alarm thresholds, and recommendation decisions into one formula adapter was considered but rejected: it obscures which behavior is a model output versus a configurable display/test policy and makes eventual formal integration harder to audit.

### D4. Keep monitoring and What-if result channels separate

Use the same adapter abstraction for a prediction of the latest currently visible monitor segment and for the fixed What-if comparison, but keep their request context and output state distinct. In snapshot mode the visible monitor prediction is based only on the selected visible rows; the What-if output belongs only to its frozen segment. The existing SPC analysis continues to receive measured rows, fixed baseline, and rules, and remains independent of model availability.

Render all alarm groups in the existing top AI Alarm area with explicit source labels: measured SPC events retain their existing renderer/event IDs; prediction risks use a separate deterministic identity and configurable test rules; What-if warnings identify the selected segment and are not presented as current-monitor state. Do not merge event queues or let one source clear/overwrite another. No timer, replay cursor, or not-yet-visible observations are introduced here; C7 owns those behaviors.

### D5. Keep Streamlit as a composition layer

Add domain calculation modules outside `ui/`; adapt `ui/tabs.py` to render selection, speed controls, unlock controls, before/after table and recommendation; adapt `ui/overview.py` to render model status and current visible prediction alerts alongside SPC. `ui/layout.py` remains the composition point and computes model-facing results from explicitly selected rows, while SPC keeps its own service and result object. Tab switching reruns must reconstruct the same values from `WorkspaceState`, not invoke random behavior or mutate source rows.

### D6. Deliver C4 interactions with an explicit prediction stub before C5 formula integration

Follow the roadmap's C4-then-C5 sequence: first make fixed-segment state, parameter allowlist/unlock, comparison table and UI testable against a deterministic port stub; then provide and wire the full formula adapter, configurable risk tests and candidate recommendation. Keep local tests at each group and C1–C3 regression at integration completion. This keeps tasks independently verifiable without claiming the stub is the delivered Mock model.

## Risks / Trade-offs

- [Formula estimates may look like calibrated model output] → Show Mock source/version, illustrative configuration and non-causal note wherever results or recommendations appear; never call the risk value a calibrated probability.
- [Configured test limits may be mistaken for official quality rules] → Bundle them only with explicit demo metadata, expose their version/source, and keep TCP-004 status unchanged.
- [Candidate state may leak into measured rows or SPC] → Use immutable snapshot plus separate allowlisted candidate map; test source bytes/rows and identical SPC result before and after slider changes.
- [Current-monitor prediction may be confused with the fixed comparison] → Use distinct result state, section headings, identities, timestamps, and source labels; test that selecting/recomputing What-if does not change current-monitor/SPC alarms.
- [A later B model may not support all output or risk capabilities] → Validate adapter capabilities and each target independently; show unavailable reason without suppressing CSV/SPC; leave official mapping for C9/TCP-004.

## Migration Plan

No persistence schema, A/B file, or external dependency migration is expected. Existing sessions begin with no What-if snapshot and initialize from the latest visible segment when data permits; existing C1–C3 state and SPC result remain intact. If an adapter or test configuration is unavailable, retain data inspection and SPC and show a local unavailable state. Rollback is limited to reverting this Change's C-only modules/UI wiring; no measured CSV or baseline is modified.
