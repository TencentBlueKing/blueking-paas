# -*- coding: utf-8 -*-
from typing import Any, Dict, List


def encode_envs(envs: Dict[str, Any]) -> List:
    """Encode Dict-like envs to k8s env list"""
    return [{"name": key, "value": str(value)} for key, value in envs.items()]


def decode_envs(envs: List) -> Dict[str, Any]:
    """Decode k8s env list to Dict-like envs"""
    return {env["name"]: env["value"] for env in envs if "name" in env and "value" in env}
