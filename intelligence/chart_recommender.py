"""Chart type recommendations based on data characteristics"""
from core.data_profiler import ColumnProfile
from typing import List, Tuple

class ChartRecommender:
    """Recommend chart types based on data characteristics"""

    def recommend(self, x_profile: ColumnProfile,
                  y_profile: ColumnProfile) -> List[Tuple[str, float]]:
        """
        Returns ranked list of chart types with confidence scores.
        Example: [('bar', 0.95), ('scatter', 0.85), ('line', 0.70)]
        """
        scores = {}

        # Bar chart: categorical x, numeric y
        if x_profile.dtype == 'categorical' and y_profile.dtype == 'numeric':
            if x_profile.cardinality < 10:
                scores['bar'] = 0.95
            elif x_profile.cardinality < 30:
                scores['bar'] = 0.85
                scores['scatter'] = 0.80

        # Line chart: temporal x, numeric y
        if x_profile.is_temporal and y_profile.dtype == 'numeric':
            scores['line'] = 0.98
            scores['area'] = 0.92
            scores['scatter'] = 0.75

        # Scatter: numeric x, numeric y
        if x_profile.dtype == 'numeric' and y_profile.dtype == 'numeric':
            scores['scatter'] = 0.95
            if y_profile.has_outliers:
                scores['scatter'] = 0.98  # Scatter shows outliers better
            if x_profile.is_temporal:
                scores['line'] = 0.90

        # Pie chart: categorical x, numeric y, low cardinality
        if x_profile.dtype == 'categorical' and y_profile.dtype == 'numeric':
            if x_profile.cardinality < 8:
                scores['pie'] = 0.85

        # Box plot: categorical x, numeric y, shows distribution
        if x_profile.dtype == 'categorical' and y_profile.dtype == 'numeric':
            if y_profile.has_outliers:
                scores['box'] = 0.90
            else:
                scores['box'] = 0.75

        # Default fallback
        if not scores:
            scores['scatter'] = 0.7

        # Return sorted by score
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
