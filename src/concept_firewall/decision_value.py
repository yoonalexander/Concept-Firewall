"""Saved-data value bounds; these are scenarios, never measured recovery."""
from __future__ import annotations

import math


def allocation_summary(y, alerts):
    import numpy as np
    y, alerts = np.asarray(y), np.asarray(alerts)
    if y.ndim != 1 or y.shape != alerts.shape or not len(y):
        raise ValueError("Aligned nonempty outcome/alert vectors required")
    if not np.isin(y, [0, 1]).all() or alerts.dtype != bool or len(np.unique(y)) != 2:
        raise ValueError("Binary outcomes, Boolean alerts and both classes required")
    n = len(y)
    failures, selected = int(y.sum()), int(alerts.sum())
    tp, fp = int(y[alerts].sum()), int((y[alerts] == 0).sum())
    prevalence, rate = failures/n, selected/n
    return {"puzzles": n, "failures": failures, "successes": n-failures,
            "alerts": selected, "true_positives": tp, "false_positives": fp,
            "failure_prevalence": prevalence, "alert_fraction": rate,
            "recall": tp/failures, "fpr": fp/(n-failures),
            "alert_precision": tp/selected if selected else 0.0,
            "random_expected_selected_failures": selected*prevalence,
            "perfect_retry_gain_ceiling": tp/n,
            "perfect_retry_advantage_over_random_all": tp/n-rate*prevalence,
            "verifier_first_expected_selected_failures": min(selected, failures),
            "selected_recovery_ratio_needed_vs_verifier_first": selected/tp if tp else None}


def recovery_scenario(summary, recovery_probability, success_damage_probability,
                      retry_cost, monitoring_cost=0.0):
    """Costs are fractions of one baseline solve; one correct answer has value 1.

    Retaining the first valid answer makes damage zero. The cost frontier uses
    correct answers / normalized compute, not latency or actual measured costs.
    """
    values = (recovery_probability, success_damage_probability, retry_cost, monitoring_cost)
    if any(not math.isfinite(v) or v < 0 for v in values) or max(values[:2]) > 1:
        raise ValueError("Invalid probability/cost scenario")
    n, tp, fp = summary["puzzles"], summary["true_positives"], summary["false_positives"]
    gain = (tp*recovery_probability-fp*success_damage_probability)/n
    base_accuracy = 1-summary["failure_prevalence"]
    extra_cost = summary["alert_fraction"]*retry_cost+monitoring_cost
    return {"recovery_probability": recovery_probability,
            "success_damage_probability": success_damage_probability,
            "retry_cost_in_baseline_solves": retry_cost,
            "monitoring_cost_in_baseline_solves": monitoring_cost,
            "hypothetical_accuracy_gain": gain,
            "extra_normalized_compute": extra_cost,
            "correct_answers_per_compute": (base_accuracy+gain)/(1+extra_cost),
            "baseline_correct_answers_per_compute": base_accuracy,
            "break_even_recovery_probability":
                (base_accuracy*extra_cost+fp/n*success_damage_probability)/(tp/n) if tp else None}


def portable_scores(record, x):
    import numpy as np
    x = np.asarray(x, dtype=float)
    mean, scale, coefficient = (np.asarray(record[k], dtype=float) for k in ("mean", "scale", "coefficient"))
    if x.ndim != 2 or x.shape[1:] != mean.shape or mean.shape != scale.shape or scale.shape != coefficient.shape:
        raise ValueError("Probe feature dimensions changed")
    if not all(np.isfinite(v).all() for v in (x, mean, scale, coefficient)) or (scale <= 0).any():
        raise ValueError("Invalid probe inputs/scales")
    if record["classes"] != [0, 1] or not math.isfinite(record["intercept"]):
        raise ValueError("Probe orientation/intercept changed")
    return (x-mean)/scale @ coefficient+record["intercept"]
