# -*- coding: utf-8 -*-
from typing import List, Optional

from attrs import define, field


@define
class VolumeMount:
    name: str
    mountPath: str
    readOnly: bool = False
    mountPropagation: Optional[str] = None
    subPath: Optional[str] = None
    # k8s 1.8 不支持该字段
    # subPathExpr: Optional[str] = None


@define
class KeyToPath:
    key: str
    path: str
    mode: int = 0o644


@define
class EmptyDirVolumeSource:
    medium: Optional[str] = None
    sizeLimit: Optional[str] = None


@define
class HostPathVolumeSource:
    path: str
    type: Optional[str] = None


@define
class SecretVolumeSource:
    secretName: str
    items: List[KeyToPath] = field(factory=list)
    optional: bool = False
    defaultMode: int = 0o644


@define
class Volume:
    name: str
    emptyDir: Optional[EmptyDirVolumeSource] = None
    hostPath: Optional[HostPathVolumeSource] = None
    secret: Optional[SecretVolumeSource] = None
