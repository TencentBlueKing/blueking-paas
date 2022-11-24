# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict

from django.conf import settings
from django.http.request import HttpRequest
from paas_service.auth import sign_instance_token
from paas_service.models import InstanceDataRepresenter, ServiceInstance

ABBREVS = ((1 << 50, 'PB'), (1 << 40, 'TB'), (1 << 30, 'GB'), (1 << 20, 'MB'), (1 << 10, 'KB'), (1, 'bytes'))


def humanize_bytes(bytevalue: int, precision=2):
    # 参考自 https://gist.github.com/moird/3684595
    if bytevalue < 1:
        return "0 byte"
    elif bytevalue == 1:
        return "1 byte"
    for factor, suffix in ABBREVS:
        if bytevalue >= factor:
            return f"{bytevalue/factor:.{precision if factor != 1 else 0}f} {suffix}"


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
