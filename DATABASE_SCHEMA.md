# AI-Insight PostgreSQL Database Schema

**Database Name:** `ai_insight`
**Owner:** To be assigned by DBA
**Created Date:** 2024
**Version:** 1.0

---

## **Table 1: users**
### Purpose
Store user account information and authentication credentials.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| user_id | SERIAL | PRIMARY KEY | Unique user identifier |
| username | VARCHAR(80) | UNIQUE, NOT NULL | Login username (alphanumeric, 5-80 chars) |
| email | VARCHAR(120) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password (never store plain text) |
| first_name | VARCHAR(100) | NOT NULL | User's first name |
| last_name | VARCHAR(100) | NOT NULL | User's last name |
| organization | VARCHAR(150) | NULL | Company/Organization name |
| job_title | VARCHAR(100) | NULL | User's job title |
| department | VARCHAR(100) | NULL | Department (Finance, IT, Operations, etc.) |
| phone | VARCHAR(20) | NULL | Contact phone number |
| is_active | BOOLEAN | DEFAULT TRUE | Account active/inactive flag |
| is_admin | BOOLEAN | DEFAULT FALSE | Admin privileges flag |
| last_login | TIMESTAMP | NULL | Last successful login timestamp |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last profile update time |

### Indexes
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
```

### Sample Insert
```sql
INSERT INTO users (username, email, password_hash, first_name, last_name, organization, job_title, department)
VALUES ('john.doe', 'john@example.com', '$2b$12$...', 'John', 'Doe', 'Acme Corp', 'Data Analyst', 'Finance');
```

---

## **Table 2: uploads**
### Purpose
Track all file and database uploads, maintain metadata about data sources.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| upload_id | SERIAL | PRIMARY KEY | Unique upload identifier |
| user_id | INTEGER | NOT NULL, FK(users) | Owner of the upload |
| source_type | VARCHAR(50) | NOT NULL | 'csv', 'excel', 'postgresql', 'mysql', 'oracle', 'sqlite' |
| source_name | VARCHAR(255) | NOT NULL | Filename or database table name |
| file_size_mb | DECIMAL(10,2) | NULL | File size in MB (for file uploads) |
| row_count | INTEGER | NOT NULL | Total number of rows |
| column_count | INTEGER | NOT NULL | Total number of columns |
| upload_path | TEXT | NOT NULL | Path to cached pickle file (.cache/...) |
| profiles_path | TEXT | NOT NULL | Path to profiles JSON (.cache/...) |
| data_hash | VARCHAR(64) | NULL | SHA-256 hash of data for deduplication |
| source_database_id | INTEGER | NULL | FK(db_connections) - if from database |
| status | VARCHAR(50) | DEFAULT 'ready' | 'uploading', 'processing', 'ready', 'error' |
| error_message | TEXT | NULL | Error details if status='error' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Upload completion time |
| expires_at | TIMESTAMP | NULL | Auto-delete date (optional: 90 days) |

### Indexes
```sql
CREATE INDEX idx_uploads_user_id ON uploads(user_id);
CREATE INDEX idx_uploads_source_type ON uploads(source_type);
CREATE INDEX idx_uploads_created_at ON uploads(created_at);
CREATE INDEX idx_uploads_data_hash ON uploads(data_hash);
```

### Sample Insert
```sql
INSERT INTO uploads (user_id, source_type, source_name, row_count, column_count, upload_path, profiles_path, status)
VALUES (1, 'csv', 'sales_data.csv', 50000, 61, '.cache/user_uploads/upload_123.pkl', '.cache/user_uploads/upload_123_profiles.json', 'ready');
```

---

## **Table 3: db_connections**
### Purpose
Store and manage database connection credentials for user's data sources.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| connection_id | SERIAL | PRIMARY KEY | Unique connection identifier |
| user_id | INTEGER | NOT NULL, FK(users) | Owner of the connection |
| connection_name | VARCHAR(255) | NOT NULL | Display name (e.g., "Production DB", "Analytics Server") |
| db_type | VARCHAR(50) | NOT NULL | 'postgresql', 'mysql', 'mssql', 'oracle', 'sqlite' |
| host | VARCHAR(255) | NOT NULL | Database server hostname/IP |
| port | INTEGER | NOT NULL | Port number (5432, 3306, 1433, 1521, etc.) |
| database_name | VARCHAR(255) | NOT NULL | Database name |
| username | VARCHAR(255) | NOT NULL | Connection username |
| password_encrypted | VARCHAR(1000) | NOT NULL | AES-256 encrypted password |
| ssl_enabled | BOOLEAN | DEFAULT FALSE | Use SSL/TLS |
| ssl_cert_path | TEXT | NULL | Path to SSL certificate |
| connection_timeout | INTEGER | DEFAULT 30 | Timeout in seconds |
| query_timeout | INTEGER | DEFAULT 300 | Query timeout in seconds |
| is_active | BOOLEAN | DEFAULT TRUE | Enable/disable without deleting |
| is_default | BOOLEAN | DEFAULT FALSE | Default connection for user |
| last_test_at | TIMESTAMP | NULL | Last successful connection test |
| last_test_status | VARCHAR(50) | NULL | 'success', 'failed' |
| test_error_message | TEXT | NULL | Error from last failed test |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Connection creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification time |

### Indexes
```sql
CREATE INDEX idx_db_connections_user_id ON db_connections(user_id);
CREATE INDEX idx_db_connections_is_active ON db_connections(is_active);
CREATE INDEX idx_db_connections_db_type ON db_connections(db_type);
```

### Sample Insert
```sql
INSERT INTO db_connections (user_id, connection_name, db_type, host, port, database_name, username, password_encrypted, is_active, is_default)
VALUES (1, 'Production PostgreSQL', 'postgresql', 'prod.db.company.com', 5432, 'sales_db', 'app_user', 'AES_ENCRYPTED_PASSWORD...', true, true);
```

---

## **Table 4: column_profiles**
### Purpose
Cache column analysis data for faster dashboard loading (optional but recommended).

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| profile_id | SERIAL | PRIMARY KEY | Unique profile identifier |
| upload_id | INTEGER | NOT NULL, FK(uploads) | Associated upload |
| column_name | VARCHAR(255) | NOT NULL | Column name from source data |
| detected_type | VARCHAR(50) | NOT NULL | 'numeric', 'categorical', 'temporal', 'boolean', 'mixed' |
| cardinality | INTEGER | NOT NULL | Number of unique values |
| missing_percentage | DECIMAL(5,2) | NOT NULL | % of missing/null values (0-100) |
| min_value | VARCHAR(255) | NULL | Min value for numeric columns |
| max_value | VARCHAR(255) | NULL | Max value for numeric columns |
| mean_value | DECIMAL(15,4) | NULL | Mean/average for numeric |
| std_deviation | DECIMAL(15,4) | NULL | Standard deviation |
| top_values | JSONB | NULL | Top 10 unique values as JSON array |
| is_temporal | BOOLEAN | DEFAULT FALSE | Is time-series column |
| has_outliers | BOOLEAN | DEFAULT FALSE | Outliers detected |
| data_quality_score | DECIMAL(3,2) | NULL | 0.0-1.0 score |

### Indexes
```sql
CREATE INDEX idx_column_profiles_upload_id ON column_profiles(upload_id);
```

---

## **Table 5: saved_dashboards**
### Purpose
Persist user dashboard configurations and settings.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| dashboard_id | SERIAL | PRIMARY KEY | Unique dashboard identifier |
| user_id | INTEGER | NOT NULL, FK(users) | Dashboard owner |
| upload_id | INTEGER | NOT NULL, FK(uploads) | Associated data source |
| dashboard_name | VARCHAR(255) | NOT NULL | User-friendly dashboard name |
| description | TEXT | NULL | Dashboard description/notes |
| kpi_selections | JSONB | NOT NULL | Selected KPIs as JSON |
| filter_selections | JSONB | NOT NULL | Selected filters as JSON |
| confirmed_dtypes | JSONB | NOT NULL | User-confirmed column types |
| chart_configs | JSONB | NULL | Chart specifications (type, x, y, etc.) |
| ai_suggestions | JSONB | NULL | LLM-generated recommendations (if used) |
| analysis_objective | TEXT | NULL | User's stated analysis objective |
| is_public | BOOLEAN | DEFAULT FALSE | Share with other users |
| is_pinned | BOOLEAN | DEFAULT FALSE | Pin to top of dashboard list |
| view_count | INTEGER | DEFAULT 0 | Number of times viewed |
| last_viewed_at | TIMESTAMP | NULL | Last access time |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification time |

### Indexes
```sql
CREATE INDEX idx_saved_dashboards_user_id ON saved_dashboards(user_id);
CREATE INDEX idx_saved_dashboards_upload_id ON saved_dashboards(upload_id);
CREATE INDEX idx_saved_dashboards_created_at ON saved_dashboards(created_at);
```

### Sample Insert
```sql
INSERT INTO saved_dashboards (user_id, upload_id, dashboard_name, kpi_selections, filter_selections, confirmed_dtypes, analysis_objective)
VALUES (1, 1, 'Q2 2024 Sales Performance', 
  '{"kpis": [{"column": "sales", "aggregation": "sum", "label": "Total Sales"}]}',
  '{"filters": [{"column": "region", "type": "dropdown"}]}',
  '{"sales": "numeric", "region": "categorical"}',
  'Analyze Q2 sales trends by region and product category');
```

---

## **Table 6: analysis_logs**
### Purpose
Audit trail for compliance and troubleshooting.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| log_id | SERIAL | PRIMARY KEY | Unique log entry identifier |
| user_id | INTEGER | NOT NULL, FK(users) | User who performed action |
| upload_id | INTEGER | NULL | FK(uploads) - Associated upload |
| dashboard_id | INTEGER | NULL | FK(saved_dashboards) - Associated dashboard |
| action_type | VARCHAR(100) | NOT NULL | 'upload', 'analyze', 'save_dashboard', 'view_dashboard', 'export', 'delete' |
| action_details | JSONB | NULL | Additional context (table names, filters used, etc.) |
| status | VARCHAR(50) | DEFAULT 'success' | 'success', 'failed', 'partial' |
| error_message | TEXT | NULL | Error details if status != 'success' |
| execution_time_ms | INTEGER | NULL | How long action took (milliseconds) |
| data_rows_processed | INTEGER | NULL | Number of rows analyzed |
| ip_address | VARCHAR(45) | NULL | User's IP address |
| user_agent | VARCHAR(500) | NULL | Browser/client info |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Action timestamp |

### Indexes
```sql
CREATE INDEX idx_analysis_logs_user_id ON analysis_logs(user_id);
CREATE INDEX idx_analysis_logs_action_type ON analysis_logs(action_type);
CREATE INDEX idx_analysis_logs_created_at ON analysis_logs(created_at);
```

### Sample Insert
```sql
INSERT INTO analysis_logs (user_id, upload_id, action_type, status, data_rows_processed, execution_time_ms)
VALUES (1, 1, 'analyze', 'success', 50000, 2345);
```

---

## **Table 7: llm_cache**
### Purpose
Cache LLM responses to avoid duplicate API calls and improve performance.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| cache_id | SERIAL | PRIMARY KEY | Unique cache entry identifier |
| upload_id | INTEGER | NOT NULL, FK(uploads) | Associated upload |
| prompt_hash | VARCHAR(64) | NOT NULL | SHA-256 hash of prompt (for deduplication) |
| prompt_text | TEXT | NOT NULL | Full prompt sent to LLM |
| llm_model | VARCHAR(100) | NOT NULL | Model used (qwen2.5-coder:14b, etc.) |
| llm_response | JSONB | NOT NULL | Complete LLM response |
| analysis_objective | TEXT | NULL | User's objective that drove this analysis |
| response_time_ms | INTEGER | NULL | LLM response time |
| tokens_used | INTEGER | NULL | Approximate token count |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Cache creation time |
| expires_at | TIMESTAMP | NULL | Cache expiration (1 month default) |

### Indexes
```sql
CREATE INDEX idx_llm_cache_upload_id ON llm_cache(upload_id);
CREATE INDEX idx_llm_cache_prompt_hash ON llm_cache(prompt_hash);
CREATE UNIQUE INDEX idx_llm_cache_unique ON llm_cache(upload_id, prompt_hash);
```

---

## **Table 8: user_preferences**
### Purpose
Store user settings and preferences for personalization.

### Columns

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| preference_id | SERIAL | PRIMARY KEY | Unique preference identifier |
| user_id | INTEGER | NOT NULL, UNIQUE, FK(users) | User associated with preferences |
| theme | VARCHAR(50) | DEFAULT 'light' | 'light', 'dark' (for future) |
| default_chart_type | VARCHAR(50) | DEFAULT 'bar' | Default chart when auto-generating |
| rows_per_page | INTEGER | DEFAULT 15 | Pagination preference |
| auto_refresh_dashboards | BOOLEAN | DEFAULT FALSE | Auto-refresh enabled |
| auto_refresh_interval_seconds | INTEGER | DEFAULT 300 | Refresh interval |
| enable_ai_suggestions | BOOLEAN | DEFAULT TRUE | Use LLM analysis |
| enable_email_notifications | BOOLEAN | DEFAULT FALSE | Email on analysis complete |
| timezone | VARCHAR(50) | DEFAULT 'UTC' | User's timezone |
| language | VARCHAR(20) | DEFAULT 'en' | Preferred language |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

---

## **Foreign Key Relationships**

```
users
  ├── uploads (user_id)
  ├── db_connections (user_id)
  ├── saved_dashboards (user_id)
  ├── analysis_logs (user_id)
  ├── user_preferences (user_id)
  └── llm_cache (via uploads)

uploads
  ├── column_profiles (upload_id)
  ├── saved_dashboards (upload_id)
  ├── analysis_logs (upload_id)
  └── llm_cache (upload_id)

db_connections
  └── uploads (source_database_id)

saved_dashboards
  ├── analysis_logs (dashboard_id)
  └── uploads (upload_id)
```

---

## **Database Creation Script (For DBA)**

```sql
-- Connect to PostgreSQL as admin
-- psql -U postgres

-- Create database
CREATE DATABASE ai_insight
    OWNER postgres
    ENCODING 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

-- Connect to new database
\c ai_insight

-- Create schema (optional, for organization)
CREATE SCHEMA app_data;
SET search_path TO app_data, public;

-- Run all table creation statements (provided in core/app_db.py)

-- Create roles (optional, for security)
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE ai_insight TO app_user;
GRANT USAGE ON SCHEMA app_data TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app_data TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app_data TO app_user;

-- Create readonly role (for reporting)
CREATE ROLE app_readonly WITH LOGIN PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE ai_insight TO app_readonly;
GRANT USAGE ON SCHEMA app_data TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA app_data TO app_readonly;

-- Backup configuration
-- Run weekly: pg_dump -U postgres -d ai_insight > ai_insight_backup.sql
```

---

## **Data Retention Policies**

| Data Type | Retention Period | Auto-Delete |
|-----------|-----------------|-------------|
| Uploads (cache files) | 90 days | Yes |
| LLM Cache | 30 days | Yes |
| Analysis Logs | 1 year | Optional |
| Saved Dashboards | Indefinite | Manual |
| User Accounts | Until deletion | Manual |

---

## **Performance Tuning Recommendations**

1. **Vacuum & Analyze**: Run daily
   ```sql
   VACUUM ANALYZE;
   ```

2. **Partitioning**: For large tables (future)
   - `analysis_logs` by date (monthly)
   - `uploads` by user_id

3. **Archive**: Move old logs to archive schema

4. **Backup Strategy**:
   - Daily full backups
   - Hourly WAL archives
   - 30-day retention

---

## **Security Considerations**

1. **Passwords**: Always AES-256 encrypted before storage
2. **SSL/TLS**: Enable for client connections
3. **Row-Level Security**: Users can only see their own data
4. **Audit Logging**: All actions logged to `analysis_logs`
5. **Data Masking**: Sensitive columns in reports
6. **Encryption**: Consider at-rest encryption for sensitive columns

---

## **Sample Queries**

```sql
-- Get dashboard usage by user
SELECT u.username, COUNT(d.dashboard_id) as dashboard_count
FROM users u
LEFT JOIN saved_dashboards d ON u.user_id = d.user_id
GROUP BY u.username
ORDER BY dashboard_count DESC;

-- Get most used data sources
SELECT source_name, source_type, COUNT(*) as usage_count
FROM uploads
GROUP BY source_name, source_type
ORDER BY usage_count DESC;

-- Audit trail for specific user
SELECT action_type, status, created_at
FROM analysis_logs
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 20;

-- Data quality report
SELECT 
  u.source_name,
  cp.column_name,
  cp.detected_type,
  cp.missing_percentage,
  cp.data_quality_score
FROM uploads u
JOIN column_profiles cp ON u.upload_id = cp.upload_id
WHERE cp.missing_percentage > 10 OR cp.data_quality_score < 0.7
ORDER BY cp.missing_percentage DESC;
```

---

**Document Version:** 1.0
**Last Updated:** 2024
**Created for:** AI-Insight Dashboard Application
