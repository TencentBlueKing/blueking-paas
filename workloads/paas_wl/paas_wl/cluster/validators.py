# -*- coding: utf-8 -*-
from typing import Dict, Optional

from rest_framework.exceptions import ValidationError

from paas_wl.cluster.serializers import IngressConfigSLZ


def validate_ingress_config(ingress_config: Optional[Dict]):
    if ingress_config is None:
        raise ValidationError("IngressConfig should not be None.")

    IngressConfigSLZ(data=ingress_config).is_valid(raise_exception=True)
