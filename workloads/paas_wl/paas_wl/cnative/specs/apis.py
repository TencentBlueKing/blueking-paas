"""Kubernetes API related utilities"""
from typing import Dict

from pydantic import BaseModel, Field

from paas_wl.utils.text import DNS_SAFE_PATTERN


class ObjectMetadata(BaseModel):
    """Kubernetes Metadata"""

    # See https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str = Field(..., regex=DNS_SAFE_PATTERN, max_length=253)
    annotations: Dict[str, str] = Field(default_factory=dict)
    generation: int = Field(default=0)
