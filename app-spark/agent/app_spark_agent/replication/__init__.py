"""Replicating one conversation's durable state to the control plane.

A Runtime is disposable; the conversation is not. Everything in this package exists so the
state directory can be thrown away with the container it lives in: the control plane ends up
holding all three channels, and a brand new Runtime can be handed the context back.

Optional by construction. With no control plane configured the Runtime builds none of this and
behaves exactly as it did before -- which is what keeps the agent runnable, and testable, on
its own.
"""

from app_spark_agent.replication.client import ControlPlaneClient, ControlPlaneError
from app_spark_agent.replication.replicator import StateReplicator

__all__ = [
    "ControlPlaneClient",
    "ControlPlaneError",
    "StateReplicator",
]
