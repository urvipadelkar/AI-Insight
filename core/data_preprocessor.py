"""Data preprocessing based on confirmed data types"""
import pandas as pd
from typing import Dict, Optional

class DataPreprocessor:
    """Apply preprocessing to columns based on confirmed data types"""

    @staticmethod
    def preprocess_column(col: str, dtype: str, series: pd.Series) -> pd.Series:
        """Convert a single column based on confirmed dtype"""
        if dtype == 'numeric':
            # Handle formatted numbers (remove commas, spaces, currency symbols)
            if series.dtype == 'object' or series.dtype == 'str':
                cleaned = series.astype(str).str.strip().str.replace(',', '').str.replace('$', '')
                return pd.to_numeric(cleaned, errors='coerce')
            else:
                return pd.to_numeric(series, errors='coerce')

        elif dtype == 'temporal':
            # Parse date strings
            return pd.to_datetime(series, errors='coerce')

        elif dtype == 'categorical':
            # Convert to string, handle None/NaN gracefully
            return series.fillna('Unknown').astype(str)

        elif dtype == 'boolean':
            # Convert to boolean
            return series.astype(bool)

        else:
            # 'ignore' or unknown type - return as-is
            return series

    @staticmethod
    def preprocess_dataframe(
        df: pd.DataFrame,
        confirmed_dtypes: Dict[str, str]
    ) -> pd.DataFrame:
        """Apply preprocessing to dataframe based on confirmed types"""
        df_processed = df.copy()

        for col, dtype in confirmed_dtypes.items():
            if col in df_processed.columns and dtype != 'ignore':
                df_processed[col] = DataPreprocessor.preprocess_column(
                    col, dtype, df_processed[col]
                )

        return df_processed

    @staticmethod
    def get_preprocessing_report(
        df: pd.DataFrame,
        confirmed_dtypes: Dict[str, str]
    ) -> Dict:
        """Generate a report of what preprocessing will be applied"""
        report = {}

        for col, dtype in confirmed_dtypes.items():
            if col not in df.columns:
                continue

            original = df[col]
            processed = DataPreprocessor.preprocess_column(col, dtype, original)

            report[col] = {
                'original_dtype': str(original.dtype),
                'confirmed_dtype': dtype,
                'original_sample': original.head(3).tolist(),
                'processed_sample': processed.head(3).tolist(),
                'original_null_count': original.isna().sum(),
                'processed_null_count': processed.isna().sum(),
                'will_change': not original.equals(processed),
            }

        return report
