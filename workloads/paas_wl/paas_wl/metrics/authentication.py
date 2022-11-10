# -*- coding: utf-8 -*-
import secrets

from django.conf import settings
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed


class BasicAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        username = request.GET.get('client_id', '')
        password = request.GET.get('user_token', '')

        if not (username and password):
            raise AuthenticationFailed('authentication failed: no valid client_id/user_token provided')

        if not secrets.compare_digest(password, settings.METRIC_CLIENT_TOKEN_DICT.get(username, '')):
            raise AuthenticationFailed('authentication failed: incorrect client_id or user_token')

        return ({'username': username, 'password': password}, None)
