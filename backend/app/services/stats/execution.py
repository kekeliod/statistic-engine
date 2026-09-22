"""Validate an analysis request and dispatch it to the right method runner."""
from __future__ import annotations

import traceback

import pandas as pd

from app.services.stats.base import AnalysisError
from app.services.stats.registry import MethodSpec, get_method
from app.services.type_inference import infer_all_types

# A role's declared dtypes are the *ideal*. These fallbacks are also accepted so
# a numeric column stored as text ("numeric-like") still satisfies a numeric role.
_DTYPE_FALLBACK = {
    "numeric": {"numeric", "binary", "ordinal"},
    "ordinal": {"ordinal", "numeric", "binary", "categorical"},
    "binary": {"binary", "categorical"},
    "categorical": {"categorical", "binary", "ordinal", "identifier"},
}


def _resolve_role(role, provided) -> list[str]:
    if provided is None:
        raise AnalysisError(f"Missing required variable role '{role.name}'.")
    cols = [provided] if isinstance(provided, str) else list(provided)
    cols = [c for c in cols if c]
    if not cols:
        raise AnalysisError(f"No column selected for '{role.name}'.")
    if role.arity == "one" and len(cols) != 1:
        raise AnalysisError(f"Role '{role.name}' takes exactly one column, got {len(cols)}.")
    return cols


def _check_dtype(role, col: str, dtype: str) -> None:
    accepted = set(role.dtypes)
    for d in list(accepted):
        accepted |= _DTYPE_FALLBACK.get(d, set())
    if dtype not in accepted:
        raise AnalysisError(
            f"Column '{col}' looks like {dtype} data, which doesn't fit the "
            f"'{role.name}' role (expects {', '.join(role.dtypes)})."
        )


def validate(spec: MethodSpec, df: pd.DataFrame, variables: dict) -> dict:
    """Returns the resolved {role: str | list[str]} mapping, or raises AnalysisError."""
    types = infer_all_types(df)
    resolved: dict[str, object] = {}
    involved: list[str] = []
    for role in spec.roles:
        cols = _resolve_role(role, variables.get(role.name))
        for c in cols:
            if c not in df.columns:
                raise AnalysisError(f"Column '{c}' is not in this dataset.")
            _check_dtype(role, c, types[c].dtype)
            involved.append(c)
        resolved[role.name] = cols[0] if role.arity == "one" else cols
    if len(set(involved)) < len(involved):
        raise AnalysisError("The same column was selected for more than one role.")
    return resolved


def run_analysis(df: pd.DataFrame, method_key: str, variables: dict, params: dict | None = None) -> dict:
    """Execute one analysis. Always returns a dict:
       {status: "complete", result: <StatResult>} or {status: "failed", error: str}.
    """
    params = {**(params or {})}
    try:
        spec = get_method(method_key)
        merged_params = {**spec.param_defaults, **params}
        resolved = validate(spec, df, variables)

        involved = []
        for v in resolved.values():
            involved.extend([v] if isinstance(v, str) else v)
        before = len(df)
        work = df[involved].copy()
        # listwise deletion happens inside each runner after type coercion, but
        # drop fully-empty rows up front so n_excluded is meaningful.
        work = work.dropna(how="all")

        result = spec.runner(work, resolved, merged_params)
        result["n_excluded"] = before - result.get("n_used", before)
        return {"status": "complete", "result": result, "error": None}
    except AnalysisError as exc:
        return {"status": "failed", "result": None, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "result": None,
            "error": f"Unexpected error while running {method_key}: {exc}",
            "_trace": traceback.format_exc(),
        }
