# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict

from django.conf import settings
from django.http.request import HttpRequest
from paas_service.auth import sign_instance_token
from paas_service.models import InstanceDataRepresenter, ServiceInstance


def render_instance_data(request: HttpRequest, instance: ServiceInstance) -> Dict:
    """Customized render function for rendering Redis instance"""
    representer = InstanceDataRepresenter(request, instance)
    representer.meta_config['should_remove_fields'] = ['password']
    data = representer.represent()
    config = data['config']

    # Append "admin_url"
    admin_url = ""
    if settings.FEATURE_FLAG_ENABLE_ADMIN:
        token = sign_instance_token(request.client.name, str(instance.uuid))
        admin_url = request.build_absolute_uri(f'/authenticate?token={token}')

    config['admin_url'] = admin_url

    return data
