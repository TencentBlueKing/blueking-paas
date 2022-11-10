# -*- coding: utf-8 -*-
from typing import Optional

import cattr
from attrs import define
from django.conf import settings

from paas_wl.workloads.resource_templates.components.base import ExecAction, HTTPGetAction, TCPSocketAction


@define
class Probe:
    exec: Optional[ExecAction] = None
    failureThreshold: int = 3
    initialDelaySeconds: Optional[int] = None
    periodSeconds: int = 10
    successThreshold: int = 1
    # k8s 1.8 不支持该字段
    # terminationGracePeriodSeconds: Optional[int] = None
    timeoutSeconds: int = 1
    httpGet: Optional[HTTPGetAction] = None
    tcpSocket: Optional[TCPSocketAction] = None


default_readiness_probe = cattr.structure(
    {
        'tcpSocket': {'port': settings.CONTAINER_PORT},
        'initialDelaySeconds': 1,
        'periodSeconds': 15,
        'failureThreshold': 6,
    },
    Probe,
)
