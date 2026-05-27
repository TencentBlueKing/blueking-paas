# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from contextlib import contextmanager
from unittest import mock

import pytest

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import BKPAAS_DEPLOY_INTERRUPTED_ANNO_KEY
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.infras.resources.base.kres import PatchType
from paasng.platform.engine.deploy.bg_command.bkapp_hook import generate_pre_release_hook_name
from paasng.platform.engine.deploy.bg_command.bkapp_hook_interrupt import interrupt_cnative_pre_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestInterruptCNativePreRelease:
    @pytest.fixture(autouse=True)
    def _setup_wl_app(self, bk_cnative_app, bk_deployment):
        engine_app = bk_deployment.app_environment.engine_app
        WlApp.objects.get_or_create(name=engine_app.name, region=engine_app.region)
        bk_deployment.bkapp_release_id = 1
        bk_deployment.save(update_fields=["bkapp_release_id", "updated"])

    @pytest.fixture()
    def mocked_k8s(self):
        """patch get_client_by_app / crd.BkApp / KPod, 返回 (bkapp_instance, kpod_instance)"""
        fake_client = mock.MagicMock()

        @contextmanager
        def fake_get_client(_wl_app):
            yield fake_client

        with (
            mock.patch(
                "paasng.platform.engine.deploy.bg_command.bkapp_hook_interrupt.get_client_by_app",
                side_effect=fake_get_client,
            ),
            mock.patch("paasng.platform.engine.deploy.bg_command.bkapp_hook_interrupt.crd.BkApp") as m_bkapp_cls,
            mock.patch("paasng.platform.engine.deploy.bg_command.bkapp_hook_interrupt.KPod") as m_kpod_cls,
        ):
            yield m_bkapp_cls.return_value, m_kpod_cls.return_value

    def test_interrupt(self, bk_deployment, mocked_k8s):
        bkapp, kpod = mocked_k8s
        env = bk_deployment.app_environment
        wl_app = env.wl_app
        bkapp_name = generate_bkapp_name(env)
        deploy_id = str(bk_deployment.bkapp_release_id)

        interrupt_cnative_pre_release(bk_deployment)

        # 1. 写入中断 annotation
        bkapp.patch.assert_called_once_with(
            name=bkapp_name,
            namespace=wl_app.namespace,
            body={"metadata": {"annotations": {BKPAAS_DEPLOY_INTERRUPTED_ANNO_KEY: deploy_id}}},
            ptype=PatchType.MERGE,
        )
        # 2. 删除 hook pod
        kpod.delete.assert_called_once_with(
            name=generate_pre_release_hook_name(bkapp_name, bk_deployment.bkapp_release_id),
            namespace=wl_app.namespace,
        )

    def test_interrupt_best_effort(self, bk_deployment, mocked_k8s):
        """两步都抛异常时, 不应向上抛出, 且都会记录日志"""
        bkapp, kpod = mocked_k8s
        bkapp.patch.side_effect = RuntimeError("patch failed")
        kpod.delete.side_effect = RuntimeError("delete failed")

        with mock.patch(
            "paasng.platform.engine.deploy.bg_command.bkapp_hook_interrupt.logger.exception"
        ) as mocked_log:
            interrupt_cnative_pre_release(bk_deployment)

        # 第一步异常不影响第二步执行
        assert bkapp.patch.called
        assert kpod.delete.called
        # 两步都记录了日志
        assert mocked_log.call_count == 2
