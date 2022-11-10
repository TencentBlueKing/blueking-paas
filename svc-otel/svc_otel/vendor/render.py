# -*- coding: utf-8 -*-
from typing import Dict

from django.conf import settings
from django.http.request import HttpRequest
from paas_service.auth import sign_instance_token
from paas_service.models import InstanceDataRepresenter, ServiceInstance


def render_instance_data(request: HttpRequest, instance: ServiceInstance) -> Dict:
    """Customized render function for rendering service instance"""
    representer = InstanceDataRepresenter(request, instance)
    representer.set_hidden_fields(["password"])
    data = representer.represent()
    config = data["config"]

    if settings.ENABLE_ADMIN:
        # NOTE: 签发管理页面的访问链接, 如果不提供管理入口, 去掉 `admin_url` 即可
        token = sign_instance_token(request.client.name, str(instance.uuid))
        admin_url = request.build_absolute_uri(f"/authenticate?token={token}")
        config["admin_url"] = admin_url

    return data
