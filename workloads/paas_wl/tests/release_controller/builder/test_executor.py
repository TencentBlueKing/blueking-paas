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
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.release_controller.builder.executor import BuildProcessExecutor
from paas_wl.utils.constants import BuildStatus
from paas_wl.utils.stream import ConsoleStream
from tests.utils.build_process import random_fake_bp

pytestmark = pytest.mark.django_db


class TestBuildProcessExecutor:
    def test_create_and_bind_build_instance(self, app):
        bp = random_fake_bp(app)
        bpe = BuildProcessExecutor(bp, ConsoleStream())

        assert bp.status != BuildStatus.SUCCESSFUL.value, "build_process status 初始值异常"
        build_instance = bpe.create_and_bind_build_instance(dict(procfile=["sth"]))
        assert str(bp.build_id) == str(build_instance.uuid), "绑定 build instance 失败"
        assert build_instance.owner == settings.BUILDER_USERNAME, "build instance 绑定 owner 异常"
        assert build_instance.procfile == ["sth"], "build instance 绑定 procfile 异常"
        assert bp.status == BuildStatus.SUCCESSFUL.value, "build_process status 未设置为 SUCCESSFUL"

    def test_execute(self, app):
        bp = random_fake_bp(app)
        bpe = BuildProcessExecutor(bp, ConsoleStream())

        # TODO: Too much mocks, both tests and codes need refactor
        with mock.patch("paas_wl.resources.base.client.K8sScheduler.get_build_log"), mock.patch(
            "paas_wl.resources.base.client.K8sScheduler.wait_build_succeeded"
        ), mock.patch(
            "paas_wl.release_controller.builder.executor.BuildProcessExecutor.start_slugbuilder"
        ), mock.patch(
            "paas_wl.resources.base.controllers.KPod.wait_for_status"
        ):
            bpe.execute()
        assert bp.status == BuildStatus.SUCCESSFUL.value, "部署失败"
