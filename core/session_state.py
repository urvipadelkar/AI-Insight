"""Session state management for multi-page dashboard"""
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
import json

@dataclass
class KPISelection:
    """User-selected KPI configuration"""
    column: str
    aggregation: str  # 'sum', 'mean', 'count', 'max', 'min'
    label: str

    def to_dict(self):
        return asdict(self)

@dataclass
class FilterSelection:
    """User-selected filter configuration"""
    column: str
    filter_type: str  # 'dropdown', 'date_range', 'numeric_range'
    label: str

    def to_dict(self):
        return asdict(self)

class SessionState:
    """Manages user session state across pages"""

    def __init__(self):
        self.confirmed_dtypes: Dict[str, str] = {}  # col → 'numeric'|'categorical'|'temporal'|'ignore'
        self.selected_kpis: List[KPISelection] = []
        self.selected_filters: List[FilterSelection] = []
        self.column_profiles: Optional[Dict] = None
        self.preprocessed_data: Optional[Dict] = None  # Will store as dict

    def set_confirmed_dtype(self, column: str, dtype: str):
        """Store confirmed data type for a column"""
        self.confirmed_dtypes[column] = dtype

    def add_kpi(self, column: str, aggregation: str, label: str):
        """Add a KPI selection"""
        kpi = KPISelection(column=column, aggregation=aggregation, label=label)
        self.selected_kpis.append(kpi)

    def remove_kpi(self, column: str):
        """Remove a KPI selection by column"""
        self.selected_kpis = [k for k in self.selected_kpis if k.column != column]

    def add_filter(self, column: str, filter_type: str, label: str):
        """Add a filter selection"""
        f = FilterSelection(column=column, filter_type=filter_type, label=label)
        self.selected_filters.append(f)

    def remove_filter(self, column: str):
        """Remove a filter selection by column"""
        self.selected_filters = [f for f in self.selected_filters if f.column != column]

    def to_dict(self) -> Dict:
        """Convert session state to JSON-serializable dict"""
        return {
            'confirmed_dtypes': self.confirmed_dtypes,
            'selected_kpis': [kpi.to_dict() for kpi in self.selected_kpis],
            'selected_filters': [f.to_dict() for f in self.selected_filters],
        }

    def from_dict(self, data: Dict):
        """Load session state from dict"""
        if data is None:
            return

        self.confirmed_dtypes = data.get('confirmed_dtypes', {})

        self.selected_kpis = [
            KPISelection(**kpi) for kpi in data.get('selected_kpis', [])
        ]

        self.selected_filters = [
            FilterSelection(**f) for f in data.get('selected_filters', [])
        ]

    @staticmethod
    def to_json(state_dict: Dict) -> str:
        """Serialize state to JSON string"""
        return json.dumps(state_dict)

    @staticmethod
    def from_json(json_str: str) -> Dict:
        """Deserialize state from JSON string"""
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except:
            return None
