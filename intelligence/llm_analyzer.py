"""LLM-based dataset analysis"""
import json
import pandas as pd
from core.data_profiler import ColumnProfile
from core.config import DashboardConfig, FilterConfig, KPIConfig, ChartConfig
from core.schemas import DashboardConfigModel
from typing import Dict, Optional
import sys

class LLMAnalyzer:
    """Analyze dataset using LLM provider"""

    def __init__(self, provider=None, config=None):
        self.provider = provider
        self.config = config

    def analyze(self, df: pd.DataFrame,
                profiles: Dict[str, ColumnProfile],
                user_context: str = None) -> DashboardConfig:
        """Analyze dataset with LLM"""

        if not self.provider:
            print("[INFO] No LLM provider configured. Skipping LLM analysis.")
            return None

        try:
            # 1. Prepare data
            profiles_json = self._profiles_to_json(profiles)
            sample_data = self._sample_to_string(df)

            print("[INFO] Sending data to LLM for analysis...")

            # 2. Call LLM
            response = self.provider.analyze_dataset(
                profiles_json,
                sample_data,
                user_context,
                self.config.include_sample_data if self.config else True
            )

            if not response or response == "{}":
                print("[WARN] LLM returned empty response")
                return None

            # 3. Parse response
            config_dict = self.provider.extract_json_response(response)

            if not config_dict:
                print("[WARN] Could not extract JSON from LLM response")
                return None

            print("[OK] LLM analysis successful")
            print(f"[INFO] LLM suggested: {len(config_dict.get('filters', []))} filters, {len(config_dict.get('kpis', []))} KPIs, {len(config_dict.get('charts', []))} charts")

            # 4. Convert to DashboardConfig with validation
            return self._dict_to_config(config_dict, df)

        except Exception as e:
            print(f"[ERROR] LLM analysis failed: {e}")
            return None

    def _profiles_to_json(self, profiles: Dict) -> str:
        """Convert ColumnProfile dict or plain dict to JSON"""
        data = {}
        for name, profile in profiles.items():
            if isinstance(profile, dict):
                data[name] = {
                    'dtype': profile.get('dtype', 'unknown'),
                    'cardinality': profile.get('cardinality', 0),
                    'missing_pct': round(profile.get('missing_pct', 0.0), 1),
                    'range': profile.get('value_range'),
                    'top_values': (profile.get('top_values') or [])[:5],
                    'is_temporal': profile.get('is_temporal', False),
                    'has_outliers': profile.get('has_outliers', False),
                }
            else:
                data[name] = {
                    'dtype': profile.dtype,
                    'cardinality': profile.cardinality,
                    'missing_pct': round(profile.missing_pct, 1),
                    'range': profile.value_range,
                    'top_values': profile.top_values[:5],
                    'is_temporal': profile.is_temporal,
                    'has_outliers': profile.has_outliers,
                }
        return json.dumps(data, indent=2, default=str)

    def _sample_to_string(self, df: pd.DataFrame) -> str:
        """Format sample data as string"""
        return df.head(5).to_string()

    def _dict_to_config(self, config_dict: dict, df: pd.DataFrame = None) -> Optional[DashboardConfig]:
        """Convert dict to DashboardConfig with validation"""
        try:
            valid_columns = set(df.columns) if df is not None else set()

            filters = []
            if 'filters' in config_dict:
                for f in config_dict.get('filters', []):
                    col = f.get('column', '')
                    if not df is None and col not in valid_columns:
                        print(f"[WARN] Filter column '{col}' not found in dataset, skipping")
                        continue
                    filters.append(FilterConfig(
                        column=col,
                        filter_type=f.get('filter_type', 'dropdown'),
                        label=f.get('label', col)
                    ))

            kpis = []
            if 'kpis' in config_dict:
                for k in config_dict.get('kpis', []):
                    # Handle both string and dict formats
                    if isinstance(k, str):
                        metric = k
                        if not df is None and metric not in valid_columns:
                            print(f"[WARN] KPI metric '{metric}' not found in dataset, skipping")
                            continue
                        kpis.append(KPIConfig(
                            metric=metric,
                            aggregation='sum',
                            label=metric.replace('_', ' ').title()
                        ))
                    else:
                        metric = k.get('metric', '')
                        if not df is None and metric not in valid_columns:
                            print(f"[WARN] KPI metric '{metric}' not found in dataset, skipping")
                            continue
                        kpis.append(KPIConfig(
                            metric=metric,
                            aggregation=k.get('aggregation', 'sum'),
                            label=k.get('label', metric.replace('_', ' ').title())
                        ))

            charts = []
            if 'charts' in config_dict:
                for i, c in enumerate(config_dict.get('charts', [])):
                    x_col = c.get('x', c.get('x_column', ''))
                    y_col = c.get('y', c.get('y_column', ''))

                    # Validate columns exist
                    if not df is None and (x_col not in valid_columns or y_col not in valid_columns):
                        if x_col not in valid_columns:
                            print(f"[WARN] Chart x_column '{x_col}' not found, skipping chart {i}")
                        if y_col not in valid_columns:
                            print(f"[WARN] Chart y_column '{y_col}' not found, skipping chart {i}")
                        continue

                    charts.append(ChartConfig(
                        chart_id=c.get('chart_id', f'chart-{i}'),
                        chart_type=c.get('type', c.get('chart_type', 'bar')),
                        x_column=x_col,
                        y_column=y_col,
                        size=c.get('size', '1/3'),
                        aggregation=c.get('aggregation', 'sum'),
                        title=c.get('title')
                    ))

            if not charts:
                print("[WARN] No valid charts generated after validation")
            if not kpis:
                print("[WARN] No valid KPIs generated after validation")
            if not filters:
                print("[WARN] No valid filters generated after validation")

            return DashboardConfig(
                filters=filters,
                kpis=kpis,
                charts=charts,
                layout_grid=config_dict.get('layout_grid', '2-col'),
                reasoning=config_dict.get('narrative', config_dict.get('reasoning', 'LLM-generated'))
            )
        except Exception as e:
            print(f"[ERROR] Failed to convert LLM response to config: {e}")
            return None
