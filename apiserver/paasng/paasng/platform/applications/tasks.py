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
import logging
from typing import cast

from celery import shared_task

from paasng.dev_resources.servicehub.manager import LocalServiceObj, mixed_service_mgr
from paasng.dev_resources.servicehub.models import ServiceEngineAppAttachment
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@shared_task
def sync_developers_to_sentry(application_id):
    """Sync the developers list to sentry"""
    application = Application.objects.get(id=application_id)
    for app_env in application.get_app_envs():
        engine_app = app_env.engine_app
        region = engine_app.region
        service_obj = mixed_service_mgr.find_by_name(name='sentry', region=region)
        service_obj = cast(LocalServiceObj, service_obj)

        if list(mixed_service_mgr.list_provisioned_rels(engine_app, service_obj)):
            # WARN: 之后的逻辑完全假设 sentry service 是一个 Local 增强服务，并不通用，但是考虑到目前
            # 使用到 patch 逻辑的地方仅此一处，所以暂时不做高层的抽象处理，保持原状。改一点是一点。
            service = service_obj.db_object
            engine_attachment = ServiceEngineAppAttachment.objects.get(
                engine_app=engine_app, service_id=service_obj.uuid
            )
            plan = engine_attachment.plan
            params = {
                'engine_app_name': engine_app.name,
                'region': region,
                'application_code': application.code,
                'application_id': application.id,
            }

            service.patch_service_instance_by_plan(plan, params)
