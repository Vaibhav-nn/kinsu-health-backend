# Kinsu Backend Async Redesign Plan

Last updated: 2026-04-03

## Goal

Bring the backend in line with the updated product flows for:

- Onboarding
- Home
- Vault
- Track
- Vitals
- Medications
- Symptoms and illness tracking
- Exercise and activity
- Family
- Profile

while also moving the app runtime to an async PostgreSQL stack.

## Current State Summary

### Backend today

- FastAPI app uses synchronous SQLAlchemy sessions.
- PostgreSQL access is synchronous via `psycopg2-binary`.
- Alembic migrations are already present and should remain the migration source of truth.
- Existing route groups cover auth, vitals, symptoms, medications, reminders, family, homescreen, illness, and vault.
- Several current routes were built around earlier UI assumptions and do not yet match the new product surface area.

### Frontend/design today

- Some screens are already API-backed.
- Many newer surfaces are still static or partially mocked in the frontend.
- The new designs introduce meaningful data-model changes, not just visual changes.

## Design Changes Identified

## 1. Onboarding

### Updated flow

The onboarding goals screen now clearly supports multi-select health goals such as:

- Manage Diabetes
- Control Blood Pressure
- Lose Weight
- Get Fitter
- Eat Healthier
- Manage Thyroid
- Reduce Stress
- Track Chronic Illness
- Organize Medical Records
- Care for Family

### Backend impact

- Keep `health_goals`, but normalize goal values into canonical IDs.
- Store both machine-safe values and user-facing labels.
- Make onboarding robust for future recommendation logic.
- Ensure DOB continues to derive age server-side.

### Backend work

- Define canonical onboarding goal enum or validated string set.
- Update onboarding/profile schemas to validate and persist these goals.
- Ensure goals can be reused by exercise recommendations and home personalization.

## 2. Home

### Updated flow

The home screen now includes:

- Greeting header with profile avatar
- Theme toggle icon
- Notifications icon with unread count
- Search box
- Habit/streak hero card
- AI Health Alert card
- Quick actions row
- Upcoming appointments section
- Today's medicines section with progress and per-dose status
- Health insights cards
- Recent records section
- Notification sheet with multiple alert types

### Backend impact

The current backend does not yet fully model:

- appointments
- home medication dose status summary
- derived health insights
- recent records summary for home
- notification feed rich enough for all shown event types

### Backend work

- Add home dashboard aggregation endpoint or expand current homescreen endpoint.
- Add appointments domain:
  - create/list/update/delete
  - upcoming summary
  - family-member scoping
- Add notification feed model/service:
  - AI insight
  - medication reminder
  - lab report ready
  - appointment reminder
  - family update
- Add home summary response:
  - vitals summary
  - medication adherence summary
  - recent vault records
  - upcoming appointments
  - alert cards

## 3. Vault

### Updated flow

The new Vault includes:

- search
- category chips
- filter button opening advanced filter sheet
- patient filter
- hospital filter
- timeframe filter
- document-type filter
- lab parameter filter
- quick links for lab trends and prescriptions
- connected services screen
- lab parameter trend screens for CBC-style metrics

### Backend impact

Current vault support is not rich enough for:

- connected provider/service status
- structured hospital metadata
- parsed lab parameters
- parameter trend history
- advanced filter combinations
- provider sync state

### Backend work

- Extend health records model:
  - provider/hospital name
  - source/service link
  - structured tags
  - document subtype
  - patient/profile scope
- Add connected services model:
  - provider name
  - provider type
  - sync status
  - last synced at
  - record count
- Add lab parameter extraction/storage model:
  - record-linked measurements
  - parameter key
  - value
  - unit
  - observed_at
  - reference range / status
- Add vault filter endpoint support for:
  - type
  - patient
  - hospital
  - timeframe
  - tags
  - lab parameter
- Add trend endpoint for lab parameters across time.

## 4. Track and Vitals

### Updated flow

Track now includes:

- Today's vitals cards
- View Trends
- Log Vitals flow that captures multiple vitals in one form
- Quick Symptom Log
- Medications preview section
- Chronic Symptom Tracker
- Illness Episodes
- Exercise & Activity

The new vitals logging flow is no longer only single-metric oriented. It behaves like a daily snapshot form.

### Backend impact

Current vitals support exists, but the new UX suggests:

- grouped daily entry/snapshot writes
- mixed single-value and paired-value entries
- richer trend aggregation

### Backend work

- Preserve existing vitals endpoints if the frontend still uses them.
- Add snapshot-friendly write support:
  - single request can log multiple vital metrics for one timestamp
- Support paired blood pressure cleanly.
- Support “today’s vitals” summary endpoint for cards.
- Expand trends endpoint to return:
  - latest value
  - percent delta
  - time series
  - missing-data handling

## 5. Symptoms and Illness Tracking

### Updated flow

New symptom-related surfaces include:

- Quick Symptom Log with predefined chips and severity slider
- Chronic Symptom Tracker with weekly frequency and trend badges
- Illness Episodes with date range, status, tags, consult count, and lab report count

### Backend impact

This requires separating:

- one-off symptom events
- recurring/chronic symptom tracking
- illness episodes as larger grouped cases

### Backend work

- Add symptom event model:
  - symptom name
  - severity
  - notes
  - occurred_at
  - profile scope
- Extend or refactor chronic symptom tracking:
  - recurrence frequency
  - weekly occurrence map
  - trend calculation
  - severity baseline
- Expand illness episodes:
  - linked symptom events
  - linked consults
  - linked vault records
  - status such as resolved or chronic
- Add summary endpoints for:
  - quick symptom save
  - chronic symptom dashboard
  - illness episode cards

## 6. Medications

### Updated flow

Medication flows now include:

- daily progress summary
- taken / missed / left counts
- per-dose status
- daily view
- weekly adherence matrix
- monthly adherence calendar
- medication creation with timing presets
- daily / weekly / monthly / SOS frequencies
- prescribing doctor

### Backend impact

The current medication model is not enough for:

- dose-level adherence events
- schedule templates
- weekly/monthly adherence analytics
- SOS medication handling
- timing preset normalization

### Backend work

- Split medication master record from medication schedule events.
- Add medication schedule model:
  - medication_id
  - schedule_type
  - timing_slot
  - scheduled_time
  - day_of_week / day_of_month
  - frequency
- Add medication dose log model:
  - scheduled occurrence
  - taken / missed / skipped
  - taken_at
  - note
- Add adherence aggregation endpoints for:
  - daily summary
  - weekly matrix
  - monthly calendar
- Expand medication create/update schemas to support:
  - dosage
  - doctor
  - timing slot
  - frequency mode

## 7. Exercise and Activity

### Updated flow

This is a new feature area with:

- summary cards for calories, duration, activity count
- log/history/recommendations tabs
- category chooser
- activity template chooser
- activity-specific forms
- weekly history
- streak tracking
- personalized recommendations

### Backend impact

There is currently no complete backend domain for this.

### Backend work

- Add activity category model or enum.
- Add activity template catalog.
- Add activity log model:
  - category
  - template/activity type
  - duration
  - parameters by type
  - estimated calories
  - profile scope
  - logged_at
- Add weekly aggregation:
  - calories burned
  - activity count
  - streak/consistency
- Add recommendations endpoint:
  - based on conditions
  - based on medications
  - based on goals
- Start with static server-side recommendations logic before any AI dependence.

## 8. Family

### Updated flow

Family now shows richer member cards with:

- name
- relation
- age
- blood group
- condition chips
- record count
- medication count
- latest activity summary such as “BP logged today”
- caregiver mode banner
- add family member CTA

### Backend impact

Current family support is partial and missing:

- blood group
- conditions list
- card summary counters
- last activity summary
- caregiver permissions model

### Backend work

- Extend family member model:
  - blood group
  - health conditions
  - maybe gender if required by design later
- Add caregiver permissions/access model:
  - viewer/editor permissions
  - scoped access areas
- Add family summary aggregation endpoint:
  - record count
  - medication count
  - most recent logged event summary
- Ensure all health domains support family-member scoping consistently.

## 9. Profile

### Observed state

Profile updates were mentioned, but no final profile screenshots were provided in this batch.

### Likely backend needs

- richer profile payload
- editable health profile
- linked services summary
- household/caregiver settings
- preferences

### Backend work

- Audit current frontend profile screen before implementation.
- Expand `/auth/profile` or add dedicated profile endpoints for:
  - demographics
  - blood group
  - goals
  - conditions
  - caregiver settings
  - linked services summary

## Async DB Migration Plan

## Why this matters

Moving the app runtime to async PostgreSQL will make the API layer more scalable and align better with:

- concurrent mobile/web requests
- dashboard aggregation endpoints
- notification polling
- future background tasks and integrations

## Current state

- Runtime DB layer is synchronous.
- Alembic works with synchronous migration connections.

## Recommended migration strategy

### Runtime

- Move FastAPI runtime to:
  - `create_async_engine`
  - `async_sessionmaker`
  - `AsyncSession`
  - PostgreSQL via `asyncpg`

### Migrations

- Keep Alembic migration execution on a sync connection path.
- Derive a sync DSN inside Alembic if the main app config is async-only.
- Do not attempt to make migrations themselves fully async.

### Refactor scope

- `app/core/database.py`
- dependency injection in `app/api/deps.py`
- route handlers using DB sessions
- services/helpers issuing ORM queries
- test setup and fixtures

### Risks

- Large cross-cutting change.
- Easy to introduce mixed sync/async bugs if only partially migrated.
- Must be done as a deliberate foundation step, not mixed casually into feature work.

## Proposed Implementation Phases

## Phase 0. Contract Freeze and Scope Check

- Compare current frontend API usage against backend route surface.
- Confirm whether profile and AI tab are in scope for this pass.
- Confirm whether we are keeping current route names stable.

## Phase 1. Async DB Foundation

- Introduce async SQLAlchemy runtime.
- Keep Alembic sync.
- Update test database/session setup.
- Validate existing route groups still work before adding new features.

## Phase 2. Data Model Expansion

- Add migrations for:
  - appointments
  - medication schedules and dose logs
  - symptom events
  - exercise/activity logs
  - connected services
  - lab parameters
  - caregiver permissions
  - profile/family metadata additions

## Phase 3. Track/Home Core API Parity

- Home dashboard aggregation
- Today’s medicines
- appointments
- notifications
- today’s vitals summary
- quick symptom logging
- richer medication responses

## Phase 4. Vault Intelligence

- advanced filters
- connected services
- record metadata improvements
- lab parameter trends

## Phase 5. Family and Profile

- enriched family cards
- family-scoped summaries
- caregiver permissions
- profile expansion

## Phase 6. Exercise & Activity

- activity logging
- history
- recommendations

## Phase 7. Validation and Hardening

- route tests
- family-scope tests
- vault filter tests
- adherence math tests
- async DB regression tests

## API/Model Gaps To Address

## New backend domains likely required

- `appointments`
- `notifications`
- `medication_schedule`
- `medication_dose_log`
- `symptom_events`
- `activity_logs`
- `activity_templates`
- `connected_services`
- `lab_parameters`
- `caregiver_permissions`

## Existing domains requiring expansion

- `users`
- `family_members`
- `health_records`
- `medications`
- `symptoms`
- `illness_episodes`
- `homescreen`
- `vitals`

## Validation Strategy

- Keep route names stable where possible.
- Add or update focused API tests by route group.
- Add aggregation tests for:
  - home summaries
  - medication adherence
  - lab trends
  - family summaries
- Smoke test migration upgrade on a fresh database.
- Smoke test migration upgrade on a database with existing tables.

## Decisions Requiring Confirmation

These are the main decisions to confirm before implementation:

1. Approve async PostgreSQL runtime migration using `asyncpg` while keeping Alembic on a sync migration path.
2. Approve adding the following new backend domains now rather than trying to overload existing tables:
   - appointments
   - medication schedules and dose logs
   - activity logging
   - connected services
   - lab parameter history
   - caregiver permissions
3. Approve treating family member data as full profile-scoped health entities, so the same APIs work for both self and family wherever possible.
4. Confirm whether Profile and AI-tab backend work should be included in this same implementation pass, or whether this pass should stop at Home, Vault, Track, Vitals, Medications, Family, and onboarding/profile basics.

## Recommended Starting Order

If approved, the safest order is:

1. Async DB runtime migration
2. Medication/adherence model expansion
3. Home dashboard aggregation
4. Vault advanced filters and lab trends
5. Family enrichment and caregiver permissions
6. Exercise/activity module
7. Profile expansion
