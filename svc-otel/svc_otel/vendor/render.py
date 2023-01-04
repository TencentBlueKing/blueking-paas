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
from paas_service.models import InstanceDataRepresenter, ServiceInstance


def render_instance_data(request: HttpRequest, instance: ServiceInstance) -> Dict:
    """Customized render function for rendering service instance"""
    representer = InstanceDataRepresenter(request, instance)
    representer.set_hidden_fields(["password"])
    data = representer.represent()
    config = data["config"]

    if settings.ENABLE_ADMIN:
        # NOTE: 签发管理页面的访问链接, 如果不提供管理入口, 去掉 `admin_url` 即可
        admin_url = "{}/?space_uid={}#/apm/application?filter-app_name={}".format(
            settings.BK_MONITORV3_URL, config['bk_monitor_space_id'], config['app_name']
        )
        config["admin_url"] = admin_url

    return data
