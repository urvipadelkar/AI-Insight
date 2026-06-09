"""
SQLAlchemy models for AI-Insight application database
Maps to PostgreSQL schema for user management, dashboards, and audit logs
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Numeric, Text, DECIMAL, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import os

Base = declarative_base()


class User(Base):
    """User account and authentication"""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    organization = Column(String(150), nullable=True)
    job_title = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    uploads = relationship("Upload", back_populates="user", cascade="all, delete-orphan")
    db_connections = relationship("DBConnection", back_populates="user", cascade="all, delete-orphan")
    saved_dashboards = relationship("SavedDashboard", back_populates="user", cascade="all, delete-orphan")
    analysis_logs = relationship("AnalysisLog", back_populates="user", cascade="all, delete-orphan")
    user_preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, email={self.email})>"


class Upload(Base):
    """Track file and database uploads"""
    __tablename__ = "uploads"
    __table_args__ = (
        Index('idx_uploads_user_id', 'user_id'),
        Index('idx_uploads_source_type', 'source_type'),
        Index('idx_uploads_created_at', 'created_at'),
    )

    upload_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    source_type = Column(String(50), nullable=False)  # csv, excel, postgresql, mysql, oracle, sqlite
    source_name = Column(String(255), nullable=False)  # filename or table name
    file_size_mb = Column(DECIMAL(10, 2), nullable=True)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    upload_path = Column(Text, nullable=False)  # .cache/user_uploads/...
    profiles_path = Column(Text, nullable=False)  # .cache/user_uploads/..._profiles.json
    data_hash = Column(String(64), nullable=True, index=True)  # SHA-256
    source_database_id = Column(Integer, ForeignKey("db_connections.connection_id"), nullable=True)
    status = Column(String(50), default='ready')  # uploading, processing, ready, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # 90-day auto-delete

    # Relationships
    user = relationship("User", back_populates="uploads")
    db_connection = relationship("DBConnection", back_populates="uploads")
    column_profiles = relationship("ColumnProfile", back_populates="upload", cascade="all, delete-orphan")
    saved_dashboards = relationship("SavedDashboard", back_populates="upload", cascade="all, delete-orphan")
    analysis_logs = relationship("AnalysisLog", back_populates="upload")
    llm_cache = relationship("LLMCache", back_populates="upload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Upload(upload_id={self.upload_id}, source_type={self.source_type}, row_count={self.row_count})>"


class DBConnection(Base):
    """Store database connection credentials"""
    __tablename__ = "db_connections"
    __table_args__ = (
        Index('idx_db_connections_user_id', 'user_id'),
        Index('idx_db_connections_is_active', 'is_active'),
    )

    connection_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    connection_name = Column(String(255), nullable=False)  # "Production DB", "Analytics Server"
    db_type = Column(String(50), nullable=False)  # postgresql, mysql, mssql, oracle, sqlite
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password_encrypted = Column(String(1000), nullable=False)  # AES-256 encrypted
    ssl_enabled = Column(Boolean, default=False)
    ssl_cert_path = Column(Text, nullable=True)
    connection_timeout = Column(Integer, default=30)
    query_timeout = Column(Integer, default=300)
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(50), nullable=True)  # success, failed
    test_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="db_connections")
    uploads = relationship("Upload", back_populates="db_connection")

    def __repr__(self):
        return f"<DBConnection(connection_id={self.connection_id}, db_type={self.db_type}, connection_name={self.connection_name})>"


class ColumnProfile(Base):
    """Cache column analysis data"""
    __tablename__ = "column_profiles"
    __table_args__ = (
        Index('idx_column_profiles_upload_id', 'upload_id'),
    )

    profile_id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey("uploads.upload_id"), nullable=False)
    column_name = Column(String(255), nullable=False)
    detected_type = Column(String(50), nullable=False)  # numeric, categorical, temporal, boolean, mixed
    cardinality = Column(Integer, nullable=False)
    missing_percentage = Column(DECIMAL(5, 2), nullable=False)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    mean_value = Column(DECIMAL(15, 4), nullable=True)
    std_deviation = Column(DECIMAL(15, 4), nullable=True)
    top_values = Column(JSON, nullable=True)  # Array of top 10 values
    is_temporal = Column(Boolean, default=False)
    has_outliers = Column(Boolean, default=False)
    data_quality_score = Column(DECIMAL(3, 2), nullable=True)  # 0.0-1.0

    # Relationships
    upload = relationship("Upload", back_populates="column_profiles")

    def __repr__(self):
        return f"<ColumnProfile(profile_id={self.profile_id}, column_name={self.column_name}, detected_type={self.detected_type})>"


class SavedDashboard(Base):
    """Persist dashboard configurations"""
    __tablename__ = "saved_dashboards"
    __table_args__ = (
        Index('idx_saved_dashboards_user_id', 'user_id'),
        Index('idx_saved_dashboards_upload_id', 'upload_id'),
        Index('idx_saved_dashboards_created_at', 'created_at'),
    )

    dashboard_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    upload_id = Column(Integer, ForeignKey("uploads.upload_id"), nullable=False)
    dashboard_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    kpi_selections = Column(JSON, nullable=False)  # {"kpis": [...]}
    filter_selections = Column(JSON, nullable=False)  # {"filters": [...]}
    confirmed_dtypes = Column(JSON, nullable=False)  # {"column": "type", ...}
    chart_configs = Column(JSON, nullable=True)
    ai_suggestions = Column(JSON, nullable=True)  # LLM recommendations
    analysis_objective = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_dashboards")
    upload = relationship("Upload", back_populates="saved_dashboards")
    analysis_logs = relationship("AnalysisLog", back_populates="saved_dashboard")

    def __repr__(self):
        return f"<SavedDashboard(dashboard_id={self.dashboard_id}, dashboard_name={self.dashboard_name})>"


class AnalysisLog(Base):
    """Audit trail for compliance"""
    __tablename__ = "analysis_logs"
    __table_args__ = (
        Index('idx_analysis_logs_user_id', 'user_id'),
        Index('idx_analysis_logs_action_type', 'action_type'),
        Index('idx_analysis_logs_created_at', 'created_at'),
    )

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    upload_id = Column(Integer, ForeignKey("uploads.upload_id"), nullable=True)
    dashboard_id = Column(Integer, ForeignKey("saved_dashboards.dashboard_id"), nullable=True)
    action_type = Column(String(100), nullable=False)  # upload, analyze, save_dashboard, view_dashboard, export, delete
    action_details = Column(JSON, nullable=True)
    status = Column(String(50), default='success')  # success, failed, partial
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    data_rows_processed = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="analysis_logs")
    upload = relationship("Upload", back_populates="analysis_logs")
    saved_dashboard = relationship("SavedDashboard", back_populates="analysis_logs")

    def __repr__(self):
        return f"<AnalysisLog(log_id={self.log_id}, user_id={self.user_id}, action_type={self.action_type})>"


class LLMCache(Base):
    """Cache LLM responses"""
    __tablename__ = "llm_cache"
    __table_args__ = (
        Index('idx_llm_cache_upload_id', 'upload_id'),
        Index('idx_llm_cache_prompt_hash', 'prompt_hash'),
    )

    cache_id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey("uploads.upload_id"), nullable=False)
    prompt_hash = Column(String(64), nullable=False)  # SHA-256
    prompt_text = Column(Text, nullable=False)
    llm_model = Column(String(100), nullable=False)
    llm_response = Column(JSON, nullable=False)
    analysis_objective = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # 30-day default

    # Relationships
    upload = relationship("Upload", back_populates="llm_cache")

    def __repr__(self):
        return f"<LLMCache(cache_id={self.cache_id}, upload_id={self.upload_id})>"


class UserPreferences(Base):
    """Store user settings and preferences"""
    __tablename__ = "user_preferences"

    preference_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, unique=True)
    theme = Column(String(50), default='light')  # light, dark
    default_chart_type = Column(String(50), default='bar')
    rows_per_page = Column(Integer, default=15)
    auto_refresh_dashboards = Column(Boolean, default=False)
    auto_refresh_interval_seconds = Column(Integer, default=300)
    enable_ai_suggestions = Column(Boolean, default=True)
    enable_email_notifications = Column(Boolean, default=False)
    timezone = Column(String(50), default='UTC')
    language = Column(String(20), default='en')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_preferences")

    def __repr__(self):
        return f"<UserPreferences(preference_id={self.preference_id}, user_id={self.user_id})>"


# ═════════════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═════════════════════════════════════════════════════════════════════════

def init_db(engine):
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")


def drop_all_tables(engine):
    """Drop all tables (WARNING: destructive)"""
    Base.metadata.drop_all(bind=engine)
    print("[WARN] All database tables dropped")
