# -*- coding: utf-8 -*-
"""Authentication between internal services, most codes were copied from paas-service package(0.2.0)
TODO: remove duplications between "paas-service" and current module by abstract a new package?
"""
import logging

from django.http import HttpRequest
from rest_framework.authentication import BaseAuthentication

from paas_wl.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class VerifiedClientRequired(BaseAuthentication):
    """Only allow requests carrying verified client info"""

    def authenticate(self, request: HttpRequest):
        client = getattr(request, 'client', None)
        if client and client.is_verified():
            # Return a none result to let other authentication classes proceed
            return None
        else:
            raise error_codes.SERVICE_AUTH_FAILED
