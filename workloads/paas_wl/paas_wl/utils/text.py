# -*- coding: utf-8 -*-
import base64

# URL path variables
PVAR_REGION = '(?P<region>[a-z0-9_-]{1,32})'
PVAR_NAME = '(?P<name>[a-z0-9_-]{1,64})'
PVAR_CLUSTER_NAME = '(?P<name>[a-z0-9_-]{1,64})'

# This pattern is widely used by kubernetes
DNS_SAFE_PATTERN = r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'


def b64encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def b64decode(text: str) -> str:
    return base64.b64decode(text.encode()).decode()
