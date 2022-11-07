# -*- coding: utf-8 -*-
import re
from typing import Dict

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_app_name(value: str):
    """
    Check that the value follows the kubernetes name constraints
    """
    match = re.match(settings.STR_APP_NAME, value)
    if not match:
        raise ValidationError("App name illegal, can only contains a-z, 0-9, -, _")


def validate_app_structure(value: Dict):
    """Error if the dict values aren't ints >= 0"""
    if any(int(v) < 0 for v in value.values()):
        raise ValidationError("number of replicas must be greater than or equal to zero")

    for proc_type in value.keys():
        if not re.match(settings.PROC_TYPE_PATTERN, proc_type):
            raise ValidationError(
                f"process type '{proc_type}' is invalid," f" must match pattern '{settings.PROC_TYPE_PATTERN}"
            )
