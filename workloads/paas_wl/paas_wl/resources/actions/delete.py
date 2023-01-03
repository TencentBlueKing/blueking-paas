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
from typing import TYPE_CHECKING

from paas_wl.platform.applications.models import Release
from paas_wl.resources.utils.app import get_scheduler_client_by_app

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import EngineApp


def delete_app_resources(app: 'EngineApp'):
    """Delete app's resources in cluster"""
    if not Release.objects.any_successful(app):
        return

    scheduler_client = get_scheduler_client_by_app(app)
    scheduler_client.delete_all_under_namespace(namespace=app.namespace)
    return
