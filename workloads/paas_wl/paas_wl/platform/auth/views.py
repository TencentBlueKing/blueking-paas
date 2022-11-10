# -*- coding: utf-8 -*-
from rest_framework import viewsets

from .internal.client import VerifiedClientRequired
from .internal.user import UserFromVerifiedClientAuthentication


class BaseEndUserViewSet(viewsets.ViewSet):
    """Base ViewSet class, provides services for end-user directly by consuming JWT token from
    other services. Consider user in JWT payload as current logged-in user"""

    authentication_classes = [VerifiedClientRequired, UserFromVerifiedClientAuthentication]
