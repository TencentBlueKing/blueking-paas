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

from paasng.platform.engine.constants import BuildStatus
from paasng.platform.engine.deploy.bg_build.shims import K8sBuildProcessExecutor
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.utils.output import ConsoleStream

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestK8sBuildProcessExecutor:
    def test_create_and_bind_build_instance(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)

        bpe = K8sBuildProcessExecutor(bk_deployment_full, build_proc, ConsoleStream())
        build_instance = bpe.create_and_bind_build_instance(dict(procfile=["sth"], image=""))
        assert str(build_proc.build_id) == str(build_instance.uuid), "绑定 build instance 失败"
        assert build_instance.owner == bk_deployment_full.operator, "build instance 绑定 owner 异常"
        assert build_instance.procfile == ["sth"], "build instance 绑定 procfile 异常"
        assert build_proc.status == BuildStatus.SUCCESSFUL.value, "build_process status 未设置为 SUCCESSFUL"

    def test_execute(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)

        bpe = K8sBuildProcessExecutor(bk_deployment_full, build_proc, ConsoleStream())
        # TODO: Too much mocks, both tests and codes need refactor
        with mock.patch(
            "paasng.platform.engine.deploy.bg_build.shims.K8sBuildProcessExecutor.start_slugbuilder"
        ), mock.patch("paasng.platform.engine.deploy.bg_build.shims.get_scheduler_client_by_app"), mock.patch(
            "paasng.platform.engine.deploy.bg_build.utils.get_schedule_config"
        ):
            bpe.execute({"image": ""})
        assert build_proc.status == BuildStatus.SUCCESSFUL.value, "部署失败"
