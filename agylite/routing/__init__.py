"""Deterministic capability routing (P8, spec §14–15, D-012)."""
from .router import ProjectFacts, Router, RoutingError, capability_ids, context_order

__all__ = ["ProjectFacts", "Router", "RoutingError", "capability_ids", "context_order"]
