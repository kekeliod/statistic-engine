"""Anthropic tool schemas, generated from the stats registry."""
from __future__ import annotations

from app.services.stats.registry import METHODS


def _method_enum() -> list[str]:
    return sorted(METHODS)


def _roles_doc() -> str:
    lines = []
    for key, spec in METHODS.items():
        roles = "; ".join(
            f"{r.name} ({r.arity}, {'/'.join(r.dtypes)})" for r in spec.roles
        )
        lines.append(f"- {key}: {spec.description} Roles: {roles}")
    return "\n".join(lines)


def analysis_tool() -> dict:
    return {
        "name": "run_statistical_analysis",
        "description": (
            "Run one registered statistical method on the active dataset. The method is "
            "executed by a deterministic engine (pandas/SciPy/statsmodels/pingouin); you "
            "never compute the numbers yourself. Returns the frequentist result, the "
            "Bayesian result (Bayes factor where one is defined), assumption checks and "
            "summary tables.\n\nMethods and their variable roles:\n" + _roles_doc()
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": _method_enum()},
                "variables": {
                    "type": "object",
                    "description": (
                        "Maps each role of the chosen method to a dataset column name "
                        "(string) or, for 'many' roles, a list of column names."
                    ),
                    "additionalProperties": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                },
                "params": {
                    "type": "object",
                    "description": "Optional. e.g. {\"alpha\": 0.05}.",
                    "additionalProperties": True,
                },
                "objective_index": {
                    "type": ["integer", "null"],
                    "description": "0-based index of the project objective this addresses, or null.",
                },
            },
            "required": ["method", "variables"],
        },
    }


def recommendations_tool() -> dict:
    return {
        "name": "record_recommendations",
        "description": (
            "Record the recommended statistical analyses. Call this exactly once with the "
            "full list. Recommend 1-3 methods per objective, ordered best first. Only use "
            "method keys from the enum. Map suggested_variables to real column names from "
            "the dataset profile."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "objective_index": {"type": ["integer", "null"]},
                            "method_key": {"type": "string", "enum": _method_enum()},
                            "rationale": {
                                "type": "string",
                                "description": "1-2 sentences: why this method fits this objective and these variables.",
                            },
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                            "suggested_variables": {
                                "type": "object",
                                "additionalProperties": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "array", "items": {"type": "string"}},
                                    ]
                                },
                            },
                            "chart_suggestion": {"type": "string"},
                            "alternative_method_key": {
                                "type": ["string", "null"],
                                "description": "Optional second-choice method key, or null.",
                            },
                        },
                        "required": ["objective_index", "method_key", "rationale", "confidence",
                                     "suggested_variables", "chart_suggestion"],
                    },
                }
            },
            "required": ["recommendations"],
        },
    }
