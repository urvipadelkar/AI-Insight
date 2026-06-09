"""Type-aware formatting for numbers, dates, and categorical values"""
import pandas as pd
from typing import Optional, Any

class Formatter:
    """Format values based on column type and profile"""

    @staticmethod
    def coerce_numeric_series(series: pd.Series, threshold: float = 0.3) -> pd.Series:
        """Convert non-numeric series to float, stripping any locale/currency formatting.

        Handles: "1,23,456.78", "₹5,000", "$12.50", "12.5%", "1.2Cr", etc.
        Returns original series unchanged if fewer than `threshold` rows convert.
        """
        if pd.api.types.is_numeric_dtype(series):
            return series
        try:
            cleaned = (
                series.astype(str)
                .str.strip()
                .str.replace(r'[^\d.\-+eE]', '', regex=True)
                .str.strip('.')
            )
            coerced = pd.to_numeric(cleaned, errors='coerce')
            if coerced.notna().sum() / max(len(series), 1) >= threshold:
                return coerced
        except Exception:
            pass
        return series

    @staticmethod
    def resolve_column(col: str, columns) -> str:
        """Best-match column name — handles LLM mis-naming like 'Sum of Amount' → 'Amount'."""
        if col in columns:
            return col
        col_lower = col.lower().strip()
        for prefix in ('sum of ', 'total ', 'count of ', 'average of ', 'avg of ',
                        'max of ', 'min of ', 'number of ', 'no of '):
            if col_lower.startswith(prefix):
                candidate = col[len(prefix):]
                if candidate in columns:
                    return candidate
                col_lower = col_lower[len(prefix):]
                break
        col_map = {c.lower().strip(): c for c in columns}
        if col_lower in col_map:
            return col_map[col_lower]
        col_norm = col_lower.replace(' ', '_').replace('-', '_')
        for orig, mapped in col_map.items():
            if orig.replace(' ', '_').replace('-', '_') == col_norm:
                return mapped
        return col

    @staticmethod
    def format_numeric(value: Any) -> str:
        """Format numeric value with appropriate scale and precision"""
        if pd.isna(value) or value is None:
            return "N/A"

        # Handle string input
        if isinstance(value, str):
            try:
                value = float(value.replace(',', '').replace('$', '').strip())
            except:
                return "N/A"

        try:
            value = float(value)
        except:
            return "N/A"

        if pd.isna(value):
            return "N/A"

        # Auto-detect format based on magnitude
        abs_val = abs(value)

        if abs_val >= 1_000_000:
            # Millions: $X.XXM
            return f"${value/1_000_000:.2f}M"
        elif abs_val >= 1_000:
            # Thousands: $X,XXX
            return f"${value:,.0f}"
        elif abs_val >= 100:
            # Hundreds: $XXX
            return f"${value:,.0f}"
        elif abs_val >= 1:
            # Integers and small decimals
            if value == int(value):
                return f"{value:,.0f}"
            else:
                return f"{value:,.2f}"
        else:
            # Small decimals
            return f"{value:.4f}"

    @staticmethod
    def format_temporal(value: Any) -> str:
        """Format date/time value"""
        if pd.isna(value) or value is None:
            return "N/A"

        # Handle string input
        if isinstance(value, str):
            try:
                value = pd.to_datetime(value)
            except:
                return "N/A"

        # Ensure it's a Timestamp
        if not isinstance(value, pd.Timestamp):
            try:
                value = pd.Timestamp(value)
            except:
                return "N/A"

        if pd.isna(value):
            return "N/A"

        # Format as YYYY-MM-DD
        return value.strftime('%Y-%m-%d')

    @staticmethod
    def format_categorical(value: Any) -> str:
        """Format categorical value"""
        if pd.isna(value) or value is None:
            return "N/A"

        return str(value).strip()

    @staticmethod
    def format_value(value: Any, dtype: str) -> str:
        """Smart formatting based on data type"""
        if dtype == 'numeric':
            return Formatter.format_numeric(value)
        elif dtype == 'temporal':
            return Formatter.format_temporal(value)
        elif dtype == 'categorical':
            return Formatter.format_categorical(value)
        else:
            return str(value) if value is not None else "N/A"

    @staticmethod
    def format_kpi_value(
        value: Any,
        dtype: str,
        aggregation: str,
    ) -> str:
        """Format KPI value with aggregation context"""
        if pd.isna(value) or value is None:
            return "N/A"

        # For aggregations, always show numeric format
        if aggregation in ['sum', 'mean', 'max', 'min']:
            return Formatter.format_numeric(value)
        elif aggregation == 'count':
            # Count should be integer
            try:
                return f"{int(value):,}"
            except:
                return str(value)
        else:
            return Formatter.format_value(value, dtype)

    @staticmethod
    def format_aggregate_result(
        result: pd.Series,
        dtype: str,
        aggregation: str,
    ) -> str:
        """Format the result of an aggregation"""
        if len(result) == 0:
            return "N/A"

        # Get the aggregated value
        if aggregation == 'sum':
            value = result.sum()
        elif aggregation == 'mean':
            value = result.mean()
        elif aggregation == 'count':
            value = result.count()
        elif aggregation == 'max':
            value = result.max()
        elif aggregation == 'min':
            value = result.min()
        else:
            value = result.iloc[0] if len(result) > 0 else None

        return Formatter.format_kpi_value(value, dtype, aggregation)
