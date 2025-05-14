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

import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paasng.platform.declarative.handlers import get_deploy_desc_handler
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.building import ApplicationBuilder, BuildProcessResultHandler, DockerBuilder
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.models import Deployment, DeployPhaseTypes
from paasng.platform.engine.phases_steps.phases import DeployPhaseManager
from paasng.platform.sourcectl.exceptions import GetAppYamlError, GetProcfileError
from tests.utils.mocks.poll_task import FakeTaskPoller

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("_init_tmpls")
@pytest.mark.parametrize("builder_class", [ApplicationBuilder, DockerBuilder])
class TestNormalApp:
    """Tests for ApplicationBuilder"""

    @pytest.fixture(autouse=True)
    def _mock_get_app_yaml(self):
        with mock.patch(
            "paasng.platform.engine.configurations.source_file.MetaDataFileReader.get_app_desc"
        ) as mocked_get_app_yaml:
            mocked_get_app_yaml.side_effect = GetAppYamlError("unknown")
            yield

    def test_failed_when_parsing_processes(self, builder_class, bk_deployment_full):
        with (
            mock.patch(
                "paasng.platform.engine.configurations.source_file.MetaDataFileReader.get_procfile"
            ) as mocked_get_procfile,
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
        ):
            mocked_get_procfile.side_effect = GetProcfileError("Invalid Procfile format")
            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = builder_class.from_deployment_id(bk_deployment_full.id)
            builder.start()

            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.FAILED.value
            assert "[Procfile] Invalid Procfile format" in deployment.err_detail

            assert mocked_stream().write_title.called
            assert mocked_stream().write_title.call_args[0][0] == "正在解析应用进程信息"
            assert mocked_stream().write_message.called
            assert (
                mocked_stream().write_message.call_args[0][0]
                == "步骤 [解析应用进程信息] 出错了，原因：处理应用描述文件失败：[app_desc] unknown; [Procfile] Invalid Procfile format。"
            )

    def test_failed_when_upload_source(self, builder_class, bk_deployment_full):
        with (
            mock.patch(
                "paasng.platform.engine.configurations.source_file.MetaDataFileReader.get_procfile"
            ) as mocked_get_procfile,
            mock.patch(
                "paasng.platform.engine.deploy.building.{}.compress_and_upload".format(builder_class.__name__)
            ) as mocked_c_and_upload,
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
        ):
            mocked_get_procfile.return_value = {"web": "gunicorn"}
            mocked_c_and_upload.side_effect = RuntimeError("Unable to upload")

            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = builder_class.from_deployment_id(bk_deployment_full.id)
            builder.start()

            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.FAILED.value
            assert deployment.err_detail == "Unable to upload"

            assert mocked_stream().write_title.called
            assert mocked_stream().write_title.call_args[0][0] == "正在上传仓库代码"
            assert mocked_stream().write_message.called
            assert mocked_stream().write_message.call_args[0][0] == "步骤 [上传仓库代码] 出错了，请稍候重试。"

    def test_start_normal(self, builder_class, bk_deployment_full):
        with (
            mock.patch(
                "paasng.platform.engine.configurations.source_file.MetaDataFileReader.get_procfile"
            ) as mocked_get_procfile,
            mock.patch("paasng.platform.engine.deploy.building.{}.compress_and_upload".format(builder_class.__name__)),
            mock.patch("paasng.platform.engine.deploy.building.BuildProcessPoller") as mocked_poller,
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
            mock.patch(
                "paasng.platform.engine.deploy.building.{}.launch_build_processes".format(builder_class.__name__)
            ) as launch_build_processes,
        ):
            mocked_get_procfile.return_value = {"web": "gunicorn"}
            # Return a fake build_process ID
            faked_build_process_id = uuid.uuid4().hex
            launch_build_processes.return_value = faked_build_process_id

            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = builder_class.from_deployment_id(bk_deployment_full.id)
            builder.start()

            # Validate deployment data
            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.PENDING.value
            assert deployment.build_process_id.hex == faked_build_process_id
            assert deployment.err_detail is None

            # Validate "start_build_process" arguments
            assert launch_build_processes.called
            (
                source_tar_path,
                bkapp_revision_id,
            ) = launch_build_processes.call_args[0]
            assert source_tar_path != ""
            assert bkapp_revision_id is None

            # Validate other arguments
            assert mocked_stream().write_title.called
            assert mocked_poller.start.called
            assert mocked_poller.start.call_args[0][0] == {
                "build_process_id": deployment.build_process_id.hex,
                "deployment_id": deployment.id,
            }


@pytest.mark.django_db(databases=["default", "workloads"])
@pytest.mark.parametrize("builder_class", [ApplicationBuilder, DockerBuilder])
class TestCloudNative:
    def test_start_build(self, builder_class, bk_cnative_app, bk_module_full, bk_deployment_full):
        # Replace the deploy desc handler to skip the metadata reading action
        desc_handler = get_deploy_desc_handler(None, {"web": "gunicorn"})
        with (
            mock.patch(
                "paasng.platform.engine.deploy.building.get_deploy_desc_handler_by_version", return_value=desc_handler
            ),
            mock.patch("paasng.platform.engine.deploy.building.{}.compress_and_upload".format(builder_class.__name__)),
            mock.patch("paasng.platform.engine.deploy.building.BuildProcessPoller") as mocked_poller,
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
            mock.patch(
                "paasng.platform.engine.deploy.building.{}.launch_build_processes".format(builder_class.__name__)
            ) as launch_build_processes,
        ):
            # Return a fake build_process ID
            faked_build_process_id = uuid.uuid4().hex
            launch_build_processes.return_value = faked_build_process_id

            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = builder_class.from_deployment_id(bk_deployment_full.id)
            builder.start()

            # Validate deployment data
            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.PENDING.value
            assert deployment.build_process_id.hex == faked_build_process_id
            assert deployment.err_detail is None

            # Validate "start_build_process" arguments
            assert launch_build_processes.called
            (
                source_tar_path,
                bkapp_revision_id,
            ) = launch_build_processes.call_args[0]
            assert source_tar_path != ""
            assert bkapp_revision_id is not None

            # Validate other arguments
            assert mocked_stream().write_title.called
            assert mocked_poller.start.called
            assert mocked_poller.start.call_args[0][0] == {
                "build_process_id": deployment.build_process_id.hex,
                "deployment_id": deployment.id,
            }


class TestBuildProcessResultHandler:
    """Tests for BuildProcessResultHandler"""

    @pytest.fixture(autouse=True)
    def _auto_binding_phases(self, bk_prod_env, deployment):
        manager = DeployPhaseManager(bk_prod_env)
        phases = manager.get_or_create_all()
        for p in phases:
            manager.attach(DeployPhaseTypes(p.type), deployment)

    @pytest.fixture()
    def deployment(self, bk_module, bk_deployment):
        bk_deployment.build_process_id = uuid.uuid4().hex
        return bk_deployment

    @pytest.mark.parametrize(
        ("result", "status"),
        [
            (CallbackResult(status=CallbackStatus.EXCEPTION), JobStatus.FAILED.value),
            (CallbackResult(status=CallbackStatus.NORMAL), JobStatus.FAILED.value),
        ],
    )
    def test_failed(self, result, status, bk_module, deployment):
        params = {"build_process_id": deployment.build_process_id, "deployment_id": deployment.id}
        BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))

        deployment.refresh_from_db()
        assert deployment.status == status

    def test_succeeded(self, bk_module, deployment):
        params = {"build_process_id": deployment.build_process_id, "deployment_id": deployment.id}
        result = CallbackResult(
            status=CallbackStatus.NORMAL,
            data={"build_id": deployment.id.hex, "build_status": JobStatus.SUCCESSFUL.value},
        )

        with mock.patch("paasng.platform.engine.deploy.building.start_release_step") as mocked_release_mgr:
            BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))
            deployment.refresh_from_db()
            assert deployment.status == JobStatus.PENDING.value
            assert mocked_release_mgr.called
