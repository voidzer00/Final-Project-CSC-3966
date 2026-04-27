import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("decision_log.json")
STATE_FILE = Path("user_state.json")


def save_decision(action, message_text, risk_score, delay, q1_answer=None, q2_answer=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "message_text": message_text,
        "risk_score": risk_score,
        "delay": delay,
        "q1_answer": q1_answer,
        "q2_answer": q2_answer,
    }

    data = []
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

    data.append(entry)
    LOG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_decisions():
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def default_state():
    return {
        "risky_clicks": 0,
        "safe_reports": 0,
        "false_reports": 0,

        # legacy / currently used by main.py
        "reaction_avg_ms": None,
        "reaction_false_starts": 0,
        "reaction_completed_trials": 0,
        "impulsivity_level": "unknown",

        # new attention-task fields
        "attention_avg_ms": None,
        "attention_completed_trials": 0,
        "attention_false_starts": 0,
        "attention_commission_errors": 0,
        "attention_omission_errors": 0,
        "attention_score": None,

        # future-friendly score fields
        "reward_score": None,
        "reward_risky_opens": 0,
        "reward_safe_choices": 0,
        "reward_trials": 0,
        "behavioral_intervention_score": None,
    }


def load_state():
    base = default_state()

    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                base.update(saved)
        except Exception:
            pass

    return base


def save_state(state):
    current = default_state()
    if isinstance(state, dict):
        current.update(state)
    STATE_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")


def classify_impulsivity(avg_ms, false_starts, commission_errors=0, omission_errors=0):
    score = 0

    if false_starts >= 3:
        score += 2
    elif false_starts >= 1:
        score += 1

    if commission_errors >= 3:
        score += 2
    elif commission_errors >= 1:
        score += 1

    if omission_errors >= 3:
        score += 1

    if avg_ms is not None and avg_ms < 260:
        score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "moderate"
    return "low"


def compute_attention_score(avg_ms, false_starts, commission_errors, omission_errors, completed_trials):
    """
    Higher score = more vulnerability / worse control.
    0 = better
    100 = worse
    """
    score = 0

    if avg_ms is not None:
        if avg_ms < 220:
            score += 20
        elif avg_ms < 260:
            score += 12
        elif avg_ms < 320:
            score += 6
        else:
            score += 2

    score += min(false_starts * 8, 24)
    score += min(commission_errors * 10, 30)
    score += min(omission_errors * 7, 21)

    if completed_trials > 0 and completed_trials < 8:
        score += 10

    return min(score, 100)


def save_attention_summary(
    results,
    false_starts,
    commission_errors=0,
    omission_errors=0,
    total_trials=None,
):
    state = load_state()

    avg_ms = round(sum(results) / len(results), 1) if results else None
    completed_trials = len(results) if total_trials is None else total_trials

    attention_score = compute_attention_score(
        avg_ms=avg_ms,
        false_starts=false_starts,
        commission_errors=commission_errors,
        omission_errors=omission_errors,
        completed_trials=completed_trials,
    )

    impulsivity_level = classify_impulsivity(
        avg_ms=avg_ms,
        false_starts=false_starts,
        commission_errors=commission_errors,
        omission_errors=omission_errors,
    )

    # new fields
    state["attention_avg_ms"] = avg_ms
    state["attention_completed_trials"] = completed_trials
    state["attention_false_starts"] = false_starts
    state["attention_commission_errors"] = commission_errors
    state["attention_omission_errors"] = omission_errors
    state["attention_score"] = attention_score

    # keep old fields too so current app logic still works
    state["reaction_avg_ms"] = avg_ms
    state["reaction_false_starts"] = false_starts
    state["reaction_completed_trials"] = completed_trials
    state["impulsivity_level"] = impulsivity_level

    save_state(state)
    return state


def save_reaction_summary(results, false_starts):
    """
    Backward-compatible wrapper.
    Old code can still call this.
    """
    return save_attention_summary(
        results=results,
        false_starts=false_starts,
        commission_errors=0,
        omission_errors=0,
        total_trials=len(results),
    )

def compute_behavioral_intervention_score(attention_score, reward_score):
    if attention_score is None and reward_score is None:
        return None
    if attention_score is None:
        return reward_score
    if reward_score is None:
        return attention_score

    return round((attention_score * 0.5) + (reward_score * 0.5), 1)


def save_reward_summary(risky_opens, safe_choices, total_trials):
    state = load_state()

    if total_trials <= 0:
        reward_score = None
    else:
        reward_score = round((risky_opens / total_trials) * 100, 1)

    state["reward_score"] = reward_score
    state["reward_risky_opens"] = risky_opens
    state["reward_safe_choices"] = safe_choices
    state["reward_trials"] = total_trials

    attention_score = state.get("attention_score")
    behavioral_score = compute_behavioral_intervention_score(attention_score, reward_score)
    state["behavioral_intervention_score"] = behavioral_score

    save_state(state)
    return state