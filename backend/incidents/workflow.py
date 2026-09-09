"""
Incident Workflow State Machine.
Enforces the strict, linear operational lifecycle:
    OPEN -> INVESTIGATING -> RESOLVED -> CLOSED

Prevents out-of-order transitions and random status changes.
"""
from typing import Dict, List
from fastapi import HTTPException, status

ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    "OPEN": ["INVESTIGATING"],
    "INVESTIGATING": ["RESOLVED"],
    "RESOLVED": ["CLOSED"],
    "CLOSED": [],
}


def validate_status_transition(current_status: str, target_status: str, incident_id: str = "") -> None:
    """
    Validates that a requested status transition adheres strictly to:
        OPEN -> INVESTIGATING -> RESOLVED -> CLOSED
    
    Raises:
        HTTPException 400 if the transition is invalid, out-of-order, or modifies a closed ticket.
    """
    curr = current_status.upper() if current_status else "OPEN"
    target = target_status.upper() if target_status else ""

    allowed = ALLOWED_TRANSITIONS.get(curr, [])
    if target not in allowed:
        prefix = f"Incident '{incident_id}': " if incident_id else ""
        if curr == "CLOSED":
            msg = f"{prefix}Incident is CLOSED and cannot be modified (terminal state)."
        elif curr == "OPEN" and target in ["RESOLVED", "CLOSED"]:
            msg = f"{prefix}Invalid transition from OPEN to {target}. Operator must start investigation first (OPEN -> INVESTIGATING -> RESOLVED -> CLOSED)."
        elif curr == "INVESTIGATING" and target == "CLOSED":
            msg = f"{prefix}Invalid transition from INVESTIGATING to CLOSED. Incident must be RESOLVED before it can be closed (INVESTIGATING -> RESOLVED -> CLOSED)."
        elif curr == target:
            msg = f"{prefix}Incident is already in '{curr}' status."
        else:
            msg = f"{prefix}Invalid status transition from '{curr}' to '{target}'. Strict workflow: OPEN -> INVESTIGATING -> RESOLVED -> CLOSED."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
