# Google Health Connect Integration Plan

Date: 2026-03-25  
Owner: Kinsu backend + Flutter app collaboration  
Status: Planned

## 1) Goal

Integrate Android Health Connect so on-device health metrics can be:

- Pulled into the Flutter app
- Synced to backend APIs
- Stored in PostgreSQL
- Reflected in Home + Track dashboards without breaking existing features

## 2) Scope

### In Scope

- Android Health Connect integration in Flutter app
- Permission flow and data-type access controls
- Sync pipeline from device -> app -> backend
- Duplicate protection and conflict handling
- Progress visibility (sync state, last sync time, failures)
- Tests for client and backend sync paths

### Out of Scope (for initial release)

- iOS HealthKit parity (planned later)
- Wear OS direct sensor ingestion
- Real-time streaming updates
- Advanced AI coaching from health signals

## 3) Target Data Types (Phase 1)

- Heart rate
- Blood glucose
- Blood pressure
- Body temperature
- Oxygen saturation (SpO2)
- Weight
- Steps (optional in phase 1; required in phase 2 if timeline permits)

## 4) Integration Architecture

1. Flutter requests Health Connect permissions for selected data types.
2. Flutter reads records from Health Connect using time windows.
3. Flutter transforms records to Kinsu API payloads.
4. Backend validates user token + payload and upserts records.
5. Backend stores source metadata (`source=health_connect`, `external_id`, `synced_at`).
6. Home/Track APIs read unified records and return latest computed values.

## 5) Progress Stages

Use this as the stage tracker.

| Stage | Name | Deliverable | Effort | Status |
|---|---|---|---|---|
| S0 | Discovery + Mapping | Final data mapping spec and API compatibility notes | 0.5-1 day | Not Started |
| S1 | Flutter Health Connect Setup | Package integration, Android manifest/query setup, permission UX | 1-2 days | Not Started |
| S2 | Sync Service (Client) | HealthConnectSyncService with incremental pull + retry queue | 1-2 days | Not Started |
| S3 | Backend Sync Contract | Endpoints/schema updates for source metadata + idempotent upsert | 1-2 days | Not Started |
| S4 | Dashboard Wiring | Home/Track reflect synced values consistently | 1 day | Not Started |
| S5 | Reliability + Edge Cases | Duplicate prevention, revoked permissions, offline replay | 1 day | Not Started |
| S6 | Testing + QA | Unit/integration/manual test checklist green | 1-2 days | Not Started |
| S7 | Rollout | Feature flags, staged enablement, monitoring docs | 0.5-1 day | Not Started |

Estimated total (at 4 hrs/day): ~2.5 to 4 weeks.

## 6) Detailed Stage Plan

## S0 - Discovery + Mapping

### Tasks

- Map Health Connect record types -> current backend models/schemas.
- Confirm unit conventions (mg/dL, bpm, C/F, kg/lb).
- Define dedupe keys per metric (`user_id + metric_type + recorded_at + source + external_id`).

### Exit Criteria

- Signed-off mapping table.
- No API contract ambiguity.

## S1 - Flutter Health Connect Setup

### Tasks

- Add health package and Android configuration.
- Build permission onboarding flow in Settings/Profile.
- Show permission state badges (granted/partial/revoked).

### Exit Criteria

- App can request + verify permissions.
- Permission denial/revocation handled with actionable UI.

## S2 - Client Sync Service

### Tasks

- Implement incremental sync window (`last_sync_at` checkpoint).
- Transform records into backend payload schema.
- Add local queue for retries when backend/network fails.

### Exit Criteria

- Manual sync succeeds for at least 3 record types.
- Failed sync retries without duplicate writes.

## S3 - Backend Sync Contract

### Tasks

- Add source metadata fields where needed.
- Add idempotent upsert behavior for synced records.
- Add migration for any new indexes/constraints.

### Exit Criteria

- Repeated sync of same payload does not create duplicates.
- Existing manual entry behavior remains unchanged.

## S4 - Dashboard Wiring

### Tasks

- Ensure Home vitals cards and Track views consume synced records.
- Recompute latest/today summaries from unified data source.
- Ensure values refresh after sync completion.

### Exit Criteria

- Newly synced value appears correctly on Home + Track.
- No hardcoded demo numbers left in target screens.

## S5 - Reliability + Edge Cases

### Tasks

- Handle permission revoked mid-session.
- Handle partial permission grants.
- Handle stale timestamps/timezone conversions.
- Add sync cooldown and rate limiting.

### Exit Criteria

- Edge-case scenarios pass manual checklist.

## S6 - Testing + QA

### Tasks

- Backend tests: sync endpoint auth, validation, upsert idempotency.
- Flutter tests: mapper tests, sync orchestration tests.
- End-to-end smoke test with sample user account.

### Exit Criteria

- Backend test suite green.
- Flutter analyze/tests green.
- Manual smoke flow green.

## S7 - Rollout

### Tasks

- Feature flag toggle (`health_connect_enabled`).
- Add operational runbook (common errors + fixes).
- Add user-facing copy for permissions and privacy.

### Exit Criteria

- Ready for controlled beta rollout.

## 7) Data and Security Requirements

- Firebase bearer token required for all sync writes.
- Only explicit user-granted data types are read.
- Do not store raw identifiers beyond required dedupe metadata.
- Add audit fields: `created_at`, `updated_at`, `source`, `synced_at`.

## 8) Risks and Mitigations

- Permission fragmentation across devices  
  Mitigation: permission health check before sync and clear UX prompts.

- Duplicate records from retries  
  Mitigation: idempotency keys + DB unique constraints.

- Inconsistent units across sources  
  Mitigation: normalize to backend canonical units at ingestion.

- App appears stale after sync  
  Mitigation: explicit refresh + optimistic local cache updates.

## 9) Definition of Done

- User can grant Health Connect permission and sync at least one metric.
- Synced values persist in PostgreSQL and survive app restart.
- Home + Track show synced values without manual refresh hacks.
- No regressions in existing vault/auth/tracking APIs.
- Test suite + QA checklist passed.

## 10) Execution Checklist

- [ ] S0 mapping approved
- [ ] S1 Android/Flutter setup done
- [ ] S2 sync service merged
- [ ] S3 backend schema + APIs merged
- [ ] S4 UI wiring complete
- [ ] S5 edge cases validated
- [ ] S6 tests green
- [ ] S7 rollout docs + flag ready

## 11) Next Action (Immediate)

Start S0 now:

1. Build a metric-by-metric mapping table against current API request schemas.
2. Propose required backend schema deltas (if any).
3. Ask for your approval before touching migrations or breaking model constraints.
