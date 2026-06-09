"""Extract insights from data"""
from dataclasses import dataclass
from core.data_profiler import ColumnProfile
from typing import Dict, List
import pandas as pd

@dataclass
class DataInsight:
    """A data insight or finding"""
    insight_type: str              # 'trend', 'outlier', 'seasonal', 'correlation', 'quality'
    description: str
    severity: str                  # 'high', 'medium', 'low'

class InsightExtractor:
    """Extract insights from data"""

    def extract(self, df: pd.DataFrame, profiles: Dict[str, ColumnProfile]) -> List[DataInsight]:
        """Extract insights from data"""
        insights = []

        # Data quality insights
        for name, profile in profiles.items():
            if profile.missing_pct > 50:
                insights.append(DataInsight(
                    insight_type='quality',
                    description=f"{name} has {profile.missing_pct:.1f}% missing values",
                    severity='high'
                ))
            elif profile.missing_pct > 20:
                insights.append(DataInsight(
                    insight_type='quality',
                    description=f"{name} has {profile.missing_pct:.1f}% missing values",
                    severity='medium'
                ))

        # Outlier insights
        for name, profile in profiles.items():
            if profile.has_outliers and profile.dtype == 'numeric':
                insights.append(DataInsight(
                    insight_type='outlier',
                    description=f"{name} contains outliers (range: {profile.value_range})",
                    severity='medium'
                ))

        # Cardinality insights
        for name, profile in profiles.items():
            if profile.cardinality == 1:
                insights.append(DataInsight(
                    insight_type='quality',
                    description=f"{name} has only one unique value",
                    severity='high'
                ))

        return insights
