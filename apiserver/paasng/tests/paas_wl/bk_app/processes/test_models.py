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
import pytest

from paas_wl.bk_app.processes.models import ProcessSpec, ProcessSpecManager
from paasng.platform.engine.models.deployment import AutoscalingConfig, ProcessTmpl

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcessSpecManager:
    """Mixin class for testing process managers"""

    def test_sync(self, wl_app):
        mgr = ProcessSpecManager(wl_app)
        mgr.sync([ProcessTmpl(name="web", command="foo", replicas=2), ProcessTmpl(name="celery", command="foo")])

        assert ProcessSpec.objects.get(engine_app=wl_app, name="web").target_replicas == 2
        assert ProcessSpec.objects.get(engine_app=wl_app, name="celery").target_replicas == 1

        mgr.sync([ProcessTmpl(name="web", command="foo", replicas=3, plan="4C1G5R")])
        web = ProcessSpec.objects.get(engine_app=wl_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=wl_app).count() == 1

        mgr.sync([ProcessTmpl(name="web", command="foo", replicas=None, plan=None)])
        web = ProcessSpec.objects.get(engine_app=wl_app, name="web")
        assert web.target_replicas == 3
        assert web.plan.name == "4C1G5R"
        assert ProcessSpec.objects.filter(engine_app=wl_app).count() == 1

    def test_switch(self, wl_app):
        # init data
        mgr = ProcessSpecManager(wl_app)
        mgr.sync([ProcessTmpl(name="web", command="foo", replicas=2), ProcessTmpl(name="celery", command="foo")])

        web = ProcessSpec.objects.get(engine_app=wl_app, name="web")
        assert web.target_replicas == 2
        assert not web.autoscaling
        assert web.scaling_config is None

        # switch to autoscaling
        mgr.sync(
            [
                ProcessTmpl(
                    name="web",
                    command="foo",
                    replicas=2,
                    autoscaling=True,
                    scaling_config=AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default"),
                ),
                ProcessTmpl(name="celery", command="foo"),
            ]
        )
        web.refresh_from_db()
        assert web.target_replicas == 2
        assert web.autoscaling
        assert web.scaling_config == AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default")

        # rollback
        mgr.sync(
            [
                ProcessTmpl(name="web", command="foo", replicas=2, autoscaling=False),
                ProcessTmpl(name="celery", command="foo"),
            ]
        )
        web.refresh_from_db()
        assert web.target_replicas == 2
        assert not web.autoscaling
        # sync 时未提供 scaling_config, 不会设置未 None
        assert web.scaling_config == AutoscalingConfig(min_replicas=1, max_replicas=3, policy="default")


class TestProcessProbeManager:
    # FIXME 补充单元测试
    ...
