# Kinsu Health Database Implementation Plan (PostgreSQL)

## 1) Goal
Create a production-ready PostgreSQL schema that persists every user-entered field used by currently available APIs, and define a phased implementation plan so backend endpoints and DB stay fully aligned.

## 2) APIs In Scope (Current)
- `POST /api/v1/auth/login`
- `POST /api/v1/vitals/`
- `GET /api/v1/vitals/`
- `GET /api/v1/vitals/trends`
- `GET /api/v1/vitals/{vital_id}`
- `DELETE /api/v1/vitals/{vital_id}`
- `POST /api/v1/symptoms/`
- `GET /api/v1/symptoms/`
- `GET /api/v1/symptoms/{symptom_id}`
- `PUT /api/v1/symptoms/{symptom_id}`
- `DELETE /api/v1/symptoms/{symptom_id}`
- `POST /api/v1/illness/`
- `GET /api/v1/illness/`
- `GET /api/v1/illness/{episode_id}`
- `PUT /api/v1/illness/{episode_id}`
- `POST /api/v1/illness/{episode_id}/details`
- `DELETE /api/v1/illness/{episode_id}`
- `POST /api/v1/medications/`
- `GET /api/v1/medications/`
- `GET /api/v1/medications/{medication_id}`
- `PUT /api/v1/medications/{medication_id}`
- `DELETE /api/v1/medications/{medication_id}`
- `POST /api/v1/reminders/`
- `GET /api/v1/reminders/`
- `GET /api/v1/reminders/timeline`
- `GET /api/v1/reminders/{reminder_id}`
- `PUT /api/v1/reminders/{reminder_id}`
- `DELETE /api/v1/reminders/{reminder_id}`
- `GET /api/v1/homescreen/overview`
- `GET /api/v1/homescreen/search`
- `GET /api/v1/homescreen/notifications`
- `POST /api/v1/homescreen/notifications`
- `PATCH /api/v1/homescreen/notifications/{notification_id}/read`
- `GET /api/v1/homescreen/preferences`
- `PUT /api/v1/homescreen/preferences/theme`

## 3) Proposed Logical Schema

### Core entities
- `users`
- `vital_logs`
- `chronic_symptoms`
- `illness_episodes`
- `illness_details`
- `medications`
- `reminders`
- `home_preferences`
- `home_notifications`

### Entity relationships
```mermaid
erDiagram
    users ||--o{ vital_logs : has
    users ||--o{ chronic_symptoms : has
    users ||--o{ illness_episodes : has
    illness_episodes ||--o{ illness_details : has
    users ||--o{ medications : has
    users ||--o{ reminders : has
    medications ||--o{ reminders : linked_optional
    users ||--|| home_preferences : has_one
    users ||--o{ home_notifications : has
```

## 4) Physical PostgreSQL Schema (Target)

### 4.1 `users`
- `id BIGSERIAL PRIMARY KEY`
- `firebase_uid VARCHAR(128) NOT NULL UNIQUE`
- `email VARCHAR(256) NOT NULL UNIQUE`
- `display_name VARCHAR(256) NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_users_firebase_uid`
  - `idx_users_email`

### 4.2 `vital_logs`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `vital_type VARCHAR(64) NOT NULL`
- `value DOUBLE PRECISION NOT NULL`
- `value_secondary DOUBLE PRECISION NULL`
- `unit VARCHAR(32) NOT NULL`
- `recorded_at TIMESTAMPTZ NOT NULL`
- `notes TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_vital_logs_user_id`
  - `idx_vital_logs_user_type_recorded_at (user_id, vital_type, recorded_at DESC)`

### 4.3 `chronic_symptoms`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `symptom_name VARCHAR(128) NOT NULL`
- `severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 10)`
- `frequency VARCHAR(32) NOT NULL`
- `body_area VARCHAR(64) NULL`
- `triggers TEXT NULL`
- `first_noticed DATE NOT NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `notes TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_chronic_symptoms_user_id`
  - `idx_chronic_symptoms_user_is_active (user_id, is_active)`

### 4.4 `illness_episodes`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `title VARCHAR(256) NOT NULL`
- `description TEXT NULL`
- `start_date DATE NOT NULL`
- `end_date DATE NULL`
- `status VARCHAR(32) NOT NULL DEFAULT 'active'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Constraints:
  - `CHECK (end_date IS NULL OR end_date >= start_date)`
- Indexes:
  - `idx_illness_episodes_user_id`
  - `idx_illness_episodes_user_status_start (user_id, status, start_date DESC)`

### 4.5 `illness_details`
- `id BIGSERIAL PRIMARY KEY`
- `episode_id BIGINT NOT NULL REFERENCES illness_episodes(id) ON DELETE CASCADE`
- `detail_type VARCHAR(32) NOT NULL`
- `content TEXT NOT NULL`
- `recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_illness_details_episode_id`
  - `idx_illness_details_episode_recorded_at (episode_id, recorded_at ASC)`

### 4.6 `medications`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `name VARCHAR(256) NOT NULL`
- `dosage VARCHAR(64) NOT NULL`
- `frequency VARCHAR(64) NOT NULL`
- `route VARCHAR(32) NOT NULL DEFAULT 'oral'`
- `start_date DATE NOT NULL`
- `end_date DATE NULL`
- `prescribing_doctor VARCHAR(256) NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `notes TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Constraints:
  - `CHECK (end_date IS NULL OR end_date >= start_date)`
- Indexes:
  - `idx_medications_user_id`
  - `idx_medications_user_is_active (user_id, is_active)`

### 4.7 `reminders`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `title VARCHAR(256) NOT NULL`
- `reminder_type VARCHAR(32) NOT NULL`
- `linked_medication_id BIGINT NULL REFERENCES medications(id) ON DELETE SET NULL`
- `scheduled_time TIME NOT NULL`
- `recurrence VARCHAR(32) NOT NULL DEFAULT 'daily'`
- `is_enabled BOOLEAN NOT NULL DEFAULT TRUE`
- `notes TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_reminders_user_id`
  - `idx_reminders_user_enabled_time (user_id, is_enabled, scheduled_time)`
  - `idx_reminders_linked_medication_id`

### 4.8 `home_preferences`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE`
- `theme_mode VARCHAR(16) NOT NULL DEFAULT 'system'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Constraints:
  - `CHECK (theme_mode IN ('light', 'dark', 'system'))`
- Indexes:
  - `idx_home_preferences_user_id`

### 4.9 `home_notifications`
- `id BIGSERIAL PRIMARY KEY`
- `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
- `notification_type VARCHAR(64) NOT NULL DEFAULT 'general'`
- `title VARCHAR(256) NOT NULL`
- `body TEXT NOT NULL`
- `action_route VARCHAR(256) NULL`
- `is_read BOOLEAN NOT NULL DEFAULT FALSE`
- `read_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Indexes:
  - `idx_home_notifications_user_id`
  - `idx_home_notifications_user_read_created (user_id, is_read, created_at DESC)`

## 5) API Field-to-DB Mapping

### 5.1 Authentication
- `POST /auth/login`
  - Writes: `users.firebase_uid`, `users.email`, `users.display_name`, timestamps
  - Reads: full `users` row

### 5.2 Vitals
- `POST /vitals/` request fields:
  - `vital_type -> vital_logs.vital_type`
  - `value -> vital_logs.value`
  - `value_secondary -> vital_logs.value_secondary`
  - `unit -> vital_logs.unit`
  - `recorded_at -> vital_logs.recorded_at`
  - `notes -> vital_logs.notes`
- Response-only derived fields:
  - trends aggregate (`avg_value`, `min_value`, `max_value`) are computed from `vital_logs`

### 5.3 Symptoms
- `POST/PUT /symptoms` fields map 1:1:
  - `symptom_name`, `severity`, `frequency`, `body_area`, `triggers`, `first_noticed`, `is_active`, `notes`
  - table: `chronic_symptoms`

### 5.4 Illness
- `POST/PUT /illness` maps to `illness_episodes`:
  - `title`, `description`, `start_date`, `end_date`, `status`
- `POST /illness/{episode_id}/details` maps to `illness_details`:
  - `detail_type`, `content`, `recorded_at`

### 5.5 Medications
- `POST/PUT /medications` maps to `medications`:
  - `name`, `dosage`, `frequency`, `route`, `start_date`, `end_date`,
  - `prescribing_doctor`, `is_active`, `notes`

### 5.6 Reminders
- `POST/PUT /reminders` maps to `reminders`:
  - `title`, `reminder_type`, `linked_medication_id`, `scheduled_time`,
  - `recurrence`, `is_enabled`, `notes`

### 5.7 Homescreen
- `POST /homescreen/notifications` -> `home_notifications`
  - `notification_type`, `title`, `body`, `action_route`
- `PATCH /homescreen/notifications/{id}/read`
  - updates `home_notifications.is_read`, `home_notifications.read_at`
- `GET/PUT /homescreen/preferences/theme` -> `home_preferences.theme_mode`

### 5.8 Derived (Not Directly Persisted)
These are currently computed from DB at request time:
- `homescreen.overview.top_bar.notification_unread_count`
- `homescreen.overview.top_half_animation.*`
- `homescreen.overview.cards.*`
- `homescreen.bottom_nav.*`
- `homescreen.search.results` list

## 6) Implementation Plan

### Phase 0: Baseline and Freeze
1. Freeze current API contracts (payload and response fields).
2. Confirm PostgreSQL DSN for local dev:
   - `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/kinsu_health`

### Phase 1: Migration Framework
1. Add Alembic to project.
2. Create baseline revision for current schema (all 9 tables).
3. Stop relying on `Base.metadata.create_all()` for long-term schema evolution.

### Phase 2: Schema Hardening
1. Add DB-level constraints listed above (`CHECK` and FK constraints).
2. Add indexes listed above for endpoint query patterns.
3. Add `updated_at` trigger strategy (optional) or keep app-level updates.

### Phase 3: Data Access Consistency
1. Ensure all write endpoints set user ownership via auth user id.
2. Ensure all read/update/delete endpoints filter by `user_id` ownership.
3. Add API-side validation for enum-like fields:
   - `illness.status`
   - `reminder.recurrence`
   - `home_preferences.theme_mode`

### Phase 4: Search and Performance
1. Keep current `ILIKE` approach as v1.
2. If search grows, add:
   - trigram indexes (`pg_trgm`) on text fields
   - optional materialized search view

### Phase 5: Test and Verify
1. Integration tests for each endpoint family (auth/vitals/symptoms/illness/medications/reminders/homescreen).
2. Constraint tests (invalid severity, invalid date ranges, invalid theme mode).
3. Query performance checks with realistic seed data.

### Phase 6: Cutover
1. Run migrations on local PostgreSQL.
2. Seed test data.
3. Validate endpoint parity vs SQLite behavior.
4. Switch default local dev docs to PostgreSQL-first.

## 7) Acceptance Checklist
- All request body fields from current APIs have a stable DB mapping.
- All resource ownership constraints enforced via FK + API filters.
- No endpoint relies on missing table/column.
- `homescreen` APIs (`overview`, `search`, notifications, preferences) fully DB-backed where intended.
- Schema changes are migration-driven (Alembic), not implicit table creation.

## 8) Open Review Decisions (Need Your Approval)
1. Keep flexible text fields (`vital_type`, `frequency`, `status`, `recurrence`) as `VARCHAR` now, or convert to PostgreSQL `ENUM` types immediately.
2. Keep `value` as `DOUBLE PRECISION` for vitals, or move to `NUMERIC(10,2)` for stricter precision.
3. Keep `triggers` and free-form notes as plain `TEXT`, or move some fields to `JSONB` for structured querying.
