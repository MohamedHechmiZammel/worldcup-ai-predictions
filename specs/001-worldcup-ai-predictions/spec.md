# Feature Specification: World Cup 2026 AI Prediction Dashboard

**Feature Branch**: `001-worldcup-ai-predictions`

**Created**: 2026-06-21

**Status**: Draft

## User Scenarios & Testing

### User Story 1 — Pre-Match Prediction Viewer (Priority: P1)

A fan or analyst opens the dashboard before a match starts and sees the AI's
predicted outcome (Win/Draw/Loss probabilities and expected final score) along with
the key factors driving that prediction (e.g., "France ranked #2 FIFA, won last 3
head-to-head meetings, Morocco missing key striker").

**Why this priority**: This is the core value proposition — giving users a data-backed
prediction before every game. It works with historical data only and is viable as an
MVP without any live feed.

**Independent Test**: Can be fully tested by navigating to an upcoming match card and
verifying that probabilities, expected score, confidence level, and top-3 influencing
factors are displayed before kick-off.

**Acceptance Scenarios**:

1. **Given** a match is scheduled but not yet started, **When** a user opens the
   dashboard, **Then** they see Win/Draw/Loss probabilities summing to 100%,
   an expected scoreline, a confidence indicator, and the top 3 prediction factors
   for that match.
2. **Given** historical data is available for both teams, **When** probabilities are
   displayed, **Then** they are labeled with the team names (not just "Home/Away").
3. **Given** a team has no recent form data, **When** the prediction is shown,
   **Then** a "Limited data" badge is shown and confidence is reduced accordingly.

---

### User Story 2 — Live Match Prediction Updates (Priority: P1)

During an ongoing match, a fan watches the dashboard update predictions in near
real-time as key events happen (a goal is scored, a red card is issued, the half-time
whistle blows). The probability bars shift visibly and immediately reflect the new
match state.

**Why this priority**: Live updates are the key differentiator over static prediction
sites. Without this, the system is just another pre-match odds tool.

**Independent Test**: Can be fully tested by observing probability changes within 30
seconds of a simulated live event being injected (goal for Team A), and verifying the
win probability for Team A increases and Team B's decreases.

**Acceptance Scenarios**:

1. **Given** a match is live and a goal is scored, **When** the event is registered,
   **Then** the win/draw/loss probabilities update within 30 seconds with a visible
   animation indicating the change direction.
2. **Given** a red card event occurs, **When** the update is processed, **Then** the
   affected team's win probability decreases and the change is labeled "Red card —
   [Player Name]" in an event log on the match card.
3. **Given** the live data feed is temporarily unavailable, **When** the dashboard
   renders, **Then** it shows the last known prediction with a "Live data paused"
   badge and a timestamp of the last successful update.

---

### User Story 3 — Full Tournament Overview (Priority: P2)

A user opens the main dashboard and sees all 64 World Cup matches organized by
group stage and knockout rounds. Each match card shows its current state (upcoming,
live, or completed), the AI prediction for upcoming/live matches, and the actual
result for completed ones.

**Why this priority**: Users need context across the whole tournament — not just a
single match. This view drives return visits and engagement throughout the tournament.

**Independent Test**: Can be tested by verifying the main page lists all scheduled
matches with correct status badges, and that completed matches show actual scores
while upcoming matches show AI predictions.

**Acceptance Scenarios**:

1. **Given** the tournament is in progress, **When** a user opens the main page,
   **Then** they see all matches grouped by stage (Group A–H, Round of 16, etc.),
   each with a status badge (Upcoming / Live / Final).
2. **Given** a match has ended, **When** the match card is displayed, **Then** it
   shows the actual final score, not an AI prediction, with an optional "Was AI
   right?" indicator.
3. **Given** a match is currently live, **When** it appears in the match list,
   **Then** it is visually highlighted (e.g., pulsing "LIVE" indicator) and shows
   the current score alongside the updated AI prediction.

---

### User Story 4 — Prediction Accuracy Tracker (Priority: P2)

An analyst wants to evaluate how well the AI model has been performing over the
course of the tournament. They view a section of the dashboard that shows the
model's historical accuracy — percentage of correct outcome predictions, average
confidence when correct vs. incorrect, and accuracy broken down by match stage.

**Why this priority**: Accuracy transparency is a constitution requirement. Without
this, users cannot evaluate the model's trustworthiness.

**Independent Test**: Can be tested by verifying that after 5+ completed matches,
the accuracy tracker shows the correct prediction count, total completed matches,
and accuracy percentage.

**Acceptance Scenarios**:

1. **Given** at least one match has been completed, **When** a user views the
   accuracy panel, **Then** they see "X of Y matches predicted correctly (Z%)".
2. **Given** the model was highly confident on a prediction it got wrong,
   **When** the accuracy breakdown is shown, **Then** high-confidence wrong
   predictions are highlighted as notable misses.
3. **Given** matches from different tournament stages have completed, **When**
   accuracy is displayed, **Then** it is broken down by stage (Group Stage vs.
   Knockout).

---

### Edge Cases

- What happens when both teams have identical historical records against each other?
  → The model falls back to FIFA rankings and recent form only; the UI shows
  "No head-to-head history" in the factors panel.
- How does the system handle a match postponement or cancellation?
  → The match card shows "Postponed" / "Cancelled" status, prediction is frozen,
  and no live updates are attempted.
- What if the live event feed delivers duplicate events (e.g., same goal twice)?
  → Deduplication must be applied at the data ingestion layer before prediction
  update is triggered; the score must never increment twice for the same event.
- What if the prediction model returns results slower than the 30-second SLA?
  → The last known prediction is displayed with a "Updating…" spinner; the UI
  never blocks on model inference.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST display Win/Draw/Loss probabilities for every
  scheduled or live World Cup 2026 match.
- **FR-002**: The system MUST display an expected final scoreline alongside outcome
  probabilities for pre-match and live states.
- **FR-003**: The system MUST show a confidence indicator (percentage range) with
  every prediction.
- **FR-004**: The system MUST display the top 3 factors influencing each prediction
  in plain language (e.g., "France ranked #2 globally").
- **FR-005**: Pre-match predictions MUST incorporate FIFA rankings, head-to-head
  record (last 10 meetings), recent form (last 5 matches), and home/neutral
  advantage.
- **FR-006**: Once a match kicks off, the system MUST update predictions within
  30 seconds of each live event: goal, red card, yellow card, substitution,
  half-time, and full-time.
- **FR-007**: Live event updates MUST be pushed to all connected clients without
  requiring a page refresh.
- **FR-008**: When the live data feed is unavailable, the system MUST display the
  most recent cached prediction with a clear "Live data unavailable" indicator
  and the last-updated timestamp.
- **FR-009**: The dashboard MUST show all 64 matches organized by tournament stage,
  each with a status indicator (Upcoming / Live / Final).
- **FR-010**: Completed matches MUST display the actual final score alongside an
  "AI was correct / incorrect" indicator.
- **FR-011**: The system MUST track and display cumulative prediction accuracy
  (correct outcomes / total completed matches) updated after every match ends.
- **FR-012**: Accuracy MUST be broken down by tournament stage (Group Stage,
  Round of 16, Quarterfinals, Semifinals, Final).
- **FR-013**: Live event ingestion MUST deduplicate events so the same event cannot
  trigger more than one prediction update.
- **FR-014**: Every prediction response MUST be tagged with the model version that
  produced it, visible in the UI on hover/expand.

### Key Entities

- **Match**: Two competing teams, scheduled date/time, venue, tournament stage,
  current status (Upcoming/Live/Final), current score (if live/final), actual
  result (if final).
- **Team**: Name, FIFA ranking, recent form (last 5 matches W/D/L), squad
  availability notes.
- **Prediction**: Linked to a Match and a model version; contains
  Win/Draw/Loss probabilities, expected score, confidence interval,
  top-3 contributing factors, timestamp of generation.
- **LiveEvent**: Match reference, event type (Goal/RedCard/YellowCard/Sub/
  HalfTime/FullTime), team, player, minute, timestamp; deduplicated by event ID.
- **ModelVersion**: Identifier, training date, description, accuracy metrics.
- **AccuracyRecord**: Per completed match — predicted outcome, actual outcome,
  model confidence, correct/incorrect flag.

## Success Criteria

- **SC-001**: Pre-match predictions are available for 100% of scheduled matches
  at least 1 hour before kick-off.
- **SC-002**: Live prediction updates appear on the dashboard within 30 seconds
  of a live event being registered by the data feed.
- **SC-003**: The dashboard remains accessible and shows cached predictions during
  live feed outages lasting up to 10 minutes with zero blank panels.
- **SC-004**: The prediction accuracy tracker is correct to within ±1% across any
  set of 10+ completed matches.
- **SC-005**: All 64 tournament matches are visible in the tournament overview
  without requiring search or filtering.
- **SC-006**: Users can identify the top 3 prediction factors for any match within
  2 seconds of opening a match card.
- **SC-007**: The system sustains live updates across all concurrent live matches
  (up to 4 simultaneous Group Stage matches) without accuracy degradation.

## Assumptions

- Live match event data will be sourced from a third-party football data API
  (e.g., API-Football, SportMonks, or Football-Data.org); API key procurement
  is the user's responsibility.
- Historical match data (pre-2026) and FIFA rankings will be seeded into the
  database before the tournament begins; the system is not responsible for
  backfilling historical data during live operation.
- The dashboard is a single-user or small-team tool (not public-facing at scale);
  concurrent user load is assumed to be under 50 simultaneous viewers.
- Mobile responsiveness is in scope for P2 — the P1 MVP targets desktop browsers.
- User authentication and access control are out of scope for this version.
- The system covers the 2026 World Cup only; it is not a generic football
  prediction platform.
