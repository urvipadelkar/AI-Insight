"""SQL WHERE clause builder with parameterized bindings."""

import logging

SUPPORTED_OPERATORS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'}

logger = logging.getLogger(__name__)


def build(conditions: list, allowed_columns=None) -> tuple:
    """Build parameterized WHERE conditions from a list of condition dicts.

    Each dict: {'column': str, 'operator': str, 'value': str}
    Returns (conditions_str, params_dict) where conditions_str does NOT include
    the 'WHERE' keyword — the caller appends it.
    Returns ("", {}) for empty / all-skipped conditions.
    """
    if not conditions:
        return ("", {})

    clauses = []
    params = {}
    param_index = 0

    for cond in conditions:
        column = cond.get('column', '').strip()
        operator = cond.get('operator', '').strip().upper()
        value = cond.get('value', '')

        # Validate column against whitelist
        if allowed_columns is not None and column not in allowed_columns:
            logger.warning(f"[query_builder] Column '{column}' not in allowed_columns — skipped.")
            continue

        # Validate operator
        if operator not in SUPPORTED_OPERATORS:
            logger.warning(f"[query_builder] Operator '{operator}' not supported — skipped.")
            continue

        if operator == 'IN':
            # Split comma-separated value string into a list
            items = [v.strip() for v in str(value).split(',') if v.strip()]
            placeholders = []
            for i, item in enumerate(items):
                key = f"p{param_index}_{i}"
                params[key] = _coerce(item)
                placeholders.append(f":{key}")
            clause = f"{column} IN ({', '.join(placeholders)})"
            clauses.append(clause)
        else:
            key = f"p{param_index}"
            params[key] = _coerce(value)
            clauses.append(f"{column} {operator} :{key}")

        param_index += 1

    if not clauses:
        return ("", {})

    return (' AND '.join(clauses), params)


def _coerce(value: str):
    """Try to cast string to int or float; fall back to string."""
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value
