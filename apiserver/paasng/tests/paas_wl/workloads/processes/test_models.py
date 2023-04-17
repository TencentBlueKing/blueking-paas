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
from typing import List

import cattr
import pytest

from paas_wl.workloads.processes.models import DeclarativeProcess, ProcessSpec, ProcessSpecManager

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcessSpecManager:
    """Mixin class for testing process managers"""

    def test_sync(self, wl_app):
        mgr = ProcessSpecManager(wl_app)
        mgr.sync(
            cattr.structure(
                [{"name": "web", "command": "foo", "replicas": 2}, {"name": "celery", "command": "foo"}],
                List[DeclarativeProcess],
            )
        )

        assert ProcessSpec.objects.get(engine_app=wl_app, name="web").target_replicas == 2
        assert ProcessSpec.objects.get(engine_app=wl_app, name="celery").target_replicas == 1

        mgr.sync(
            cattr.structure(
                [{"name": "web", "command": "foo", "replicas": 3, "plan": "4C1G5R"}], List[DeclarativeProcess]
            )
        )
        web = ProcessSpec.objects.get(engine_app=wl_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=wl_app).count() == 1

        mgr.sync(
            cattr.structure(
                [{"name": "web", "command": "foo", "replicas": None, "plan": None}], List[DeclarativeProcess]
            )
        )
        web = ProcessSpec.objects.get(engine_app=wl_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=wl_app).count() == 1
