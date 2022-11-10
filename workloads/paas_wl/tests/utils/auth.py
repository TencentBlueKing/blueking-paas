# -*- coding: utf-8 -*-
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.token import LoginToken
from bkpaas_auth.models import User


def create_user(username='somebody', provider_type=ProviderType.RTX):
    token = LoginToken(login_token='any_token', expires_in=86400)
    return User(token=token, provider_type=provider_type, username=username)
