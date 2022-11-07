# -*- coding: utf-8 -*-
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration


def init_sentry_sdk():
    """Register celery error events to sentry"""
    from django.conf import settings

    if settings.SENTRY_CONFIG:
        # 初始化 sentry_sdk
        sentry_sdk.init(  # type: ignore
            dsn=settings.SENTRY_CONFIG["dsn"],
            integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=settings.SENTRY_CONFIG.get('traces_sample_rate', 1.0),
            # If you wish to associate users to errors (assuming you are using
            # django.contrib.auth) you may enable sending PII data.
            send_default_pii=True,
        )
