"""Pydantic schemas for validation"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any

class ColumnProfileModel(BaseModel):
    """Schema for column profile data"""
    name: str
    dtype: str
    cardinality: int
    missing_pct: float
    is_key_field: bool = False
    is_temporal: bool = False
    value_range: Optional[tuple] = None
    top_values: List[str] = []
    variance: Optional[float] = None
    skewness: Optional[float] = None
    has_outliers: bool = False

    class Config:
        extra = "allow"

class DashboardConfigModel(BaseModel):
    """Schema for dashboard configuration from LLM"""
    filters: List[dict]
    kpis: List[dict]
    charts: List[dict]
    layout_grid: str = "2-col"
    reasoning: str = ""

    class Config:
        extra = "allow"  # Allow extra fields from LLM responses
