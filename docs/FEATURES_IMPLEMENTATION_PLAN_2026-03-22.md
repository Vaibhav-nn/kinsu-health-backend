# Kinsu Feature Implementation Plan (2026-03-22)

## Objective
Implement the following features without breaking existing behavior across backend and frontend:

1. Today's Vitals pull-up details from Home trend cards.
2. Family Members linking via phone number + tracking on behalf of family members.
3. Account Switcher on Home (top-left under profile) with real data context switching.
4. Vault search + advanced filters for faster navigation.

## Repos In Scope
- Backend: `/Users/deovratsingh/Code/kinsu-health-backend`
- Frontend: `/Users/deovratsingh/Code/kinsu_health_app`

## Non-Breaking Principles
- Do not rename existing working routes.
- Additive API changes only (new endpoints/optional query params/optional headers).
- Preserve default current behavior when new params are not sent.
- Add tests before/with changes for new behaviors.
- Keep Firebase auth flow unchanged (`Authorization: Bearer <idToken>`).

## Feature Plan

## 1) Today's Vitals Pull-Up From Home Trend Card
### Current state
- Home already displays trend cards and uses vitals provider/service.
- Details behavior already exists in track vitals flow.

### Implementation
- Frontend:
  - Add tap action on each Home trend card to open a pull-up sheet/modal.
  - Reuse existing vitals detail UI component patterns from track details screen.
  - Pull data from `VitalsProvider` using existing `/api/v1/vitals` and `/api/v1/vitals/trends`.
- Backend:
  - No route changes required if current fields are enough.
  - Optional: add `latest_only=true` or `days=7` query support later only if needed.

### Acceptance criteria
- Tapping a Home trend card opens a pull-up details view.
- Data matches the corresponding vital trend and recent entries.
- Existing track vitals screens continue to work unchanged.

## 2) Family Members Linking by Phone + Tracking Support
### Current state
- Family UI is mostly static/demo data.
- Backend has no family link model/API yet.

### Implementation
- Backend (additive):
  - New tables:
    - `family_members` (id, owner_user_id, display_name, phone_e164, relation, dob, notes, is_active, created_at, updated_at)
    - `family_link_requests` (id, owner_user_id, phone_e164, status, invited_at, accepted_at)
  - New APIs under `/api/v1/family`:
    - `POST /members` (add by phone + profile info)
    - `GET /members` (list linked members)
    - `GET /members/{id}`
    - `PUT /members/{id}`
    - `DELETE /members/{id}` (soft delete preferred)
  - Tracking context support:
    - Add optional header `X-Profile-Id` to track APIs (`vitals`, `symptoms`, `illness`, `medications`, `reminders`, `homescreen` reads).
    - Default when header missing: current signed-in user profile (no behavior change).
    - Validate ownership: user can only access own linked profiles.
- Frontend:
  - Family screens wired to new APIs.
  - Add member by phone input (E.164 normalization + validation).
  - Store selected active profile in provider/state.
  - Send `X-Profile-Id` automatically from API interceptor when non-self profile selected.

### Acceptance criteria
- User can add/edit/delete family member profiles by phone.
- User can switch to a family member and log/view data for that member.
- Own profile behavior remains unchanged when no family member is selected.

## 3) Account Switcher (Home top-left under profile)
### Current state
- Home profile area exists but no functional account/profile switcher.

### Implementation
- Frontend:
  - Add account/profile switcher widget below profile section on Home.
  - Show current profile + dropdown/list of:
    - Self profile
    - Linked family profiles
  - On selection:
    - Update active profile state.
    - Trigger refresh of home + track datasets in selected context.
- Backend:
  - No dedicated switch endpoint required if `X-Profile-Id` is used.

### Acceptance criteria
- Switcher is visible and functional in required location.
- Switching profile immediately changes loaded datasets.
- No regressions in navigation or auth.

## 4) Vault Search + Filters
### Current state
- Vault supports `record_type`, `page`, `limit` only.

### Implementation
- Backend: extend `GET /api/v1/vault/records` with optional filters:
  - `q` (title/notes contains)
  - `start_date`, `end_date`
  - `has_file` (true/false)
  - `sort_by` (`record_date`, `created_at`, `title`)
  - `sort_order` (`asc`, `desc`)
- Frontend (Vault screen):
  - Add search bar + filter chips/sheet:
    - Record Type
    - Date range
    - Has attachment
    - Sort
  - Debounced search input.
  - Preserve pagination behavior.

### Acceptance criteria
- Vault records can be filtered and searched without breaking upload/view/delete flows.
- Existing basic list still works when no filters are applied.

## Data + Migration Plan
- Additive Alembic migrations only.
- New family tables + indexes.
- Optional index for vault search fields (`record_type`, `record_date`, `title`).
- Keep old data intact.

## Test Plan
### Backend
- Extend API tests for:
  - Family CRUD and ownership checks.
  - `X-Profile-Id` scoping across track/home endpoints.
  - Vault filter combinations and pagination.
- Keep existing tests green (auth, vitals, symptoms, illness, meds, reminders, vault).

### Frontend
- Widget tests:
  - Home trend pull-up opens and shows data.
  - Account switcher state updates.
  - Vault filters update list query correctly.
- Manual E2E smoke:
  - Self profile logging.
  - Family profile logging.
  - Vault search/filter + upload remains working.

## Rollout Order
1. Backend schema + family APIs + profile context support.
2. Backend vault filter query extensions.
3. Frontend family wiring + account switcher.
4. Frontend home vitals pull-up.
5. Frontend vault filters UI.
6. Full regression testing and bug fixes.

## Risk Controls
- Keep all existing endpoint paths intact.
- Gate new behavior behind optional inputs (`X-Profile-Id`, new query params).
- Verify with full unit/integration test pass before merge.

## Confirmation Gates Before Coding
1. Confirm family data model fields (especially required fields + soft delete vs hard delete).
2. Confirm profile context method: optional header `X-Profile-Id`.
3. Confirm vault filter set and sort options.
4. Confirm account switcher UX layout details.

