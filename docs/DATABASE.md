# Database ERD

```mermaid
erDiagram
  USERS ||--o{ MEMBERSHIPS : has
  ORGANIZATIONS ||--o{ MEMBERSHIPS : contains
  ORGANIZATIONS ||--o{ PROJECTS : owns
  PROJECTS ||--o{ PROJECT_KEYS : issues
  PROJECTS ||--o{ ISSUES : groups
  PROJECTS ||--o{ EVENTS : receives
  ISSUES ||--o{ EVENTS : contains
  ISSUES ||--o{ ISSUE_ACTIVITY : records
  USERS ||--o{ ISSUE_ACTIVITY : performs
  USERS ||--o{ ISSUES : assigned_to

  USERS { string id PK string email UK string name string password_hash datetime created_at }
  ORGANIZATIONS { string id PK string name string slug UK datetime created_at }
  MEMBERSHIPS { string id PK string organization_id FK string user_id FK string role }
  PROJECTS { string id PK string organization_id FK string name string platform datetime created_at }
  PROJECT_KEYS { string id PK string project_id FK string key_hash UK string key_prefix bool is_active }
  ISSUES { string id PK string project_id FK string fingerprint string title string severity string status string priority int event_count int affected_users datetime first_seen datetime last_seen }
  EVENTS { string id PK string event_id UK string project_id FK string issue_id FK string message string stacktrace json context json tags datetime created_at }
  ISSUE_ACTIVITY { string id PK string issue_id FK string actor_user_id FK string action string detail datetime created_at }
```

Key constraints: unique normalized user email; unique organization slug; unique `(organization_id, user_id)` membership; unique hashed project key; unique `(project_id, fingerprint)` issue; unique event ID. Fingerprints are scoped to project. Event tags and context are JSON/JSONB-compatible SQLAlchemy JSON columns.
