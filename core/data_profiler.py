"""Data profiling and analysis"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass
class ColumnProfile:
    """Profile of a single column"""
    name: str
    dtype: str                    # 'numeric', 'categorical', 'temporal', 'boolean', 'mixed'
    cardinality: int             # unique value count
    missing_pct: float           # % of NaN
    is_key_field: bool           # Primary key candidate?
    value_range: Optional[tuple] # (min, max) for numeric
    top_values: list             # Top 5-10 categories
    is_temporal: bool
    variance: Optional[float]    # For numeric
    skewness: Optional[float]    # Distribution shape
    has_outliers: bool

    def __repr__(self):
        return f"{self.name} ({self.dtype}, card={self.cardinality})"

class DataProfiler:
    """Analyze dataset and generate column profiles"""

    def profile(self, df: pd.DataFrame) -> Dict[str, ColumnProfile]:
        """Analyze each column and return profiles"""
        profiles = {}

        for col in df.columns:
            series = df[col]
            dtype = self._detect_type(series)
            cardinality = series.nunique()
            missing_pct = series.isna().sum() / len(series) * 100

            # Numeric column analysis
            if dtype == 'numeric':
                # Convert to numeric if not already (handle thousands separators)
                if series.dtype != 'numeric':
                    try:
                        cleaned = series.astype(str).str.strip().str.replace(',', '').str.replace(' ', '')
                        numeric_series = pd.to_numeric(cleaned, errors='coerce')
                    except:
                        numeric_series = pd.to_numeric(series, errors='coerce')
                else:
                    numeric_series = series

                value_range = (float(numeric_series.min()), float(numeric_series.max()))
                variance = float(numeric_series.var()) if numeric_series.var() > 0 else 0
                skewness = float(numeric_series.skew()) if not numeric_series.empty else 0
                has_outliers = self._detect_outliers_iqr(numeric_series)
            else:
                value_range = None
                variance = None
                skewness = None
                has_outliers = False

            is_temporal = self._is_temporal(series)
            top_values = series.value_counts().head(10).index.astype(str).tolist() if cardinality > 1 else []

            profiles[col] = ColumnProfile(
                name=col,
                dtype=dtype,
                cardinality=cardinality,
                missing_pct=missing_pct,
                is_key_field=cardinality == len(df),  # Unique per row
                value_range=value_range,
                top_values=top_values,
                is_temporal=is_temporal,
                variance=variance,
                skewness=skewness,
                has_outliers=has_outliers,
            )

        return profiles

    def _detect_type(self, series: pd.Series) -> str:
        """Detect column type"""
        if pd.api.types.is_numeric_dtype(series):
            return 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(series):
            return 'temporal'
        elif pd.api.types.is_bool_dtype(series):
            return 'boolean'
        else:
            # Try to detect numeric-looking string columns
            if series.dtype in ('object', 'str'):
                try:
                    # Try to convert to numeric, handling thousands separators
                    cleaned = series.astype(str).str.strip().str.replace(',', '').str.replace(' ', '')
                    numeric_series = pd.to_numeric(cleaned, errors='coerce')
                    # If >70% of values convert to numeric, it's a numeric column
                    if numeric_series.notna().sum() / len(series) > 0.7:
                        return 'numeric'
                except:
                    pass

            return 'categorical'

    def _is_temporal(self, series: pd.Series) -> bool:
        """Check if column is temporal"""
        # Check if already datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return True

        # Check if string column (object or str dtype)
        if series.dtype in ('object', 'str') or pd.api.types.is_string_dtype(series):
            col_lower = series.name.lower()
            # Check for date-related keywords
            if any(keyword in col_lower for keyword in ['date', 'time', 'created', 'posted', 'parking', 'inward', 'invoice']):
                # Check if values can be parsed as dates
                try:
                    parsed = pd.to_datetime(series, errors='coerce')
                    if len(parsed) > 0 and parsed.notna().sum() / len(parsed) > 0.5:
                        return True
                except:
                    pass

        return False

    def _detect_outliers_iqr(self, series: pd.Series) -> bool:
        """Detect outliers using IQR method"""
        try:
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            return ((series < Q1 - 1.5 * IQR) | (series > Q3 + 1.5 * IQR)).any()
        except:
            return False

def get_key_metrics(profiles: Dict[str, ColumnProfile]) -> List[str]:
    """Identify likely metric columns (numeric, not IDs)"""
    metrics = []
    for name, profile in profiles.items():
        if profile.dtype == 'numeric' and not profile.is_key_field and profile.missing_pct < 50:
            metrics.append(name)
    return metrics

def get_filter_candidates(profiles: Dict[str, ColumnProfile]) -> List[str]:
    """Identify likely filter columns (low cardinality categorical)"""
    candidates = []
    for name, profile in profiles.items():
        if profile.dtype == 'categorical' and 2 < profile.cardinality < 50 and not profile.is_key_field:
            candidates.append(name)
    return candidates
