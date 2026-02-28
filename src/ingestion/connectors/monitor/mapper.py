"""
Helper functions for interpreting Monitor metric records.
Used by the right-sizing rule engine, not for direct DB storage
(metrics are ephemeral — stored in raw layer only).
"""
from __future__ import annotations

from typing import Any

CPU_METRIC = "Percentage CPU"
MEMORY_METRIC = "Available Memory Bytes"
LOW_CPU_THRESHOLD = 10.0      # % — flag VM for right-sizing
LOW_MEMORY_THRESHOLD_GB = 2.0  # GB available — flag VM for right-sizing


def is_underutilised_vm(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyse metric records for a single VM and return utilisation summary.
    Returns a dict with flags the rule engine consumes.
    """
    cpu_record = next((m for m in metrics if m["metric_name"] == CPU_METRIC), None)
    mem_record = next((m for m in metrics if m["metric_name"] == MEMORY_METRIC), None)

    cpu_avg = cpu_record["avg_value"] if cpu_record else None
    cpu_p95 = cpu_record["p95_value"] if cpu_record else None
    mem_avg_bytes = mem_record["avg_value"] if mem_record else None
    mem_avg_gb = (mem_avg_bytes / (1024 ** 3)) if mem_avg_bytes is not None else None

    return {
        "cpu_avg_pct": cpu_avg,
        "cpu_p95_pct": cpu_p95,
        "mem_available_avg_gb": mem_avg_gb,
        "is_low_cpu": (cpu_avg is not None and cpu_avg < LOW_CPU_THRESHOLD),
        "is_low_memory_pressure": (
            mem_avg_gb is not None and mem_avg_gb > LOW_MEMORY_THRESHOLD_GB
        ),
        "sample_count": cpu_record["sample_count"] if cpu_record else 0,
        "lookback_days": cpu_record["lookback_days"] if cpu_record else 0,
    }
