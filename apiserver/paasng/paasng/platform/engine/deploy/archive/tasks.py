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
from celery import shared_task

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.networking.ingress.kres_entities.ingress import ingress_kmodel
from paas_wl.workloads.networking.ingress.kres_entities.service import service_kmodel


@shared_task
def archive_related_resources(wl_app_id):
    """应用下架时，下架相关资源（service、pre-release-hook、ingress）

    :param str wl_app_id: wl_app uuid
    """
    wl_app = WlApp.objects.get(uuid=wl_app_id)

    # 回收 service
    services = service_kmodel.list_by_app(wl_app)
    for service in services:
        service_kmodel.delete(service)

    # 回收 ingress
    ingresses = ingress_kmodel.list_by_app(wl_app)
    for ingress in ingresses:
        ingress_kmodel.delete(ingress)

    # 回收 pre-release-hook
    client = get_client_by_app(wl_app)
    KPod(client).delete(name="pre-release-hook", namespace=wl_app.namespace)
