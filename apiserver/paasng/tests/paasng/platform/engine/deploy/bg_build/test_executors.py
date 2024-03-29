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
import base64
import json
import time
from typing import Dict
from unittest import mock

import pytest

from paasng.infras.bk_ci import entities
from paasng.infras.bk_ci.constants import PipelineBuildStatus
from paasng.platform.engine.constants import BuildStatus
from paasng.platform.engine.deploy.bg_build.executors import (
    DefaultBuildProcessExecutor,
    PipelineBuildProcessExecutor,
)
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.utils.output import NullStream

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDefaultBuildProcessExecutor:
    def test_create_and_bind_build_instance(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)

        bpe = DefaultBuildProcessExecutor(bk_deployment_full, build_proc, NullStream())
        build_instance = bpe.create_and_bind_build_instance(dict(procfile=["sth"], image=""))
        assert str(build_proc.build_id) == str(build_instance.uuid), "绑定 build instance 失败"
        assert build_instance.owner == bk_deployment_full.operator, "build instance 绑定 owner 异常"
        assert build_proc.status == BuildStatus.SUCCESSFUL, "build_process status 未设置为 SUCCESSFUL"

    def test_execute(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)

        bpe = DefaultBuildProcessExecutor(bk_deployment_full, build_proc, NullStream())
        # TODO: Too much mocks, both tests and codes need refactor
        with mock.patch(
            "paasng.platform.engine.deploy.bg_build.executors.DefaultBuildProcessExecutor.start_slugbuilder"
        ), mock.patch("paasng.platform.engine.deploy.bg_build.executors.BuildHandler"), mock.patch(
            "paasng.platform.engine.deploy.bg_build.executors.NamespacesHandler"
        ), mock.patch("paasng.platform.engine.deploy.bg_build.utils.get_schedule_config"):
            bpe.execute({"image": ""})
        assert build_proc.status == BuildStatus.SUCCESSFUL, "部署失败"


class StubBkCIPipelineClient:
    def __init__(self, *args, **kwargs):
        pass

    def start_build(self, pipeline: entities.Pipeline, start_params: Dict[str, str]) -> entities.PipelineBuild:
        return entities.PipelineBuild(projectId=pipeline.projectId, pipelineId=pipeline.pipelineId, buildId="b-123456")

    def retrieve_build_status(self, build: entities.PipelineBuild) -> entities.PipelineBuildStatus:
        cur_timestamp = int(time.time())
        return entities.PipelineBuildStatus(
            buildId=build.buildId,
            startTime=cur_timestamp - 1,
            endTime=cur_timestamp,
            status=PipelineBuildStatus.SUCCEED,
            currentTimestamp=cur_timestamp,
            stageStatus=[],
            totalTime=1,
            executeTime=1,
        )

    def retrieve_full_log(self, build: entities.PipelineBuild) -> entities.PipelineLogModel:
        cur_timestamp = int(time.time())
        return entities.PipelineLogModel(
            buildId=build.buildId,
            finished=True,
            hasMore=False,
            logs=[
                entities.PipelineLogLine(
                    lineNo=idx,
                    timestamp=cur_timestamp + idx,
                    message=f"this is message {idx}",
                    priority="INFO",
                    tag="e-xxx",
                    subTag="se-xxx",
                    jobId="c-xxx",
                    executeCount=1,
                )
                for idx in range(10)
            ],
            timeUsed=1,
        )


class TestPipelineBuildProcessExecutor:
    def test_execute(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)

        with mock.patch(
            "paasng.platform.engine.deploy.bg_build.executors.BkCIPipelineClient", new=StubBkCIPipelineClient
        ):
            bpe = PipelineBuildProcessExecutor(bk_deployment_full, build_proc, NullStream())
            bpe.execute(
                {
                    "image": "busybox:latest",
                    "image_repository": "dockerhub.com",
                    "use_dockerfile": True,
                }
            )

        assert build_proc.status == BuildStatus.SUCCESSFUL

    def test_build_env_vars_params(self, bk_deployment_full, build_proc):
        attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
        bpe = PipelineBuildProcessExecutor(bk_deployment_full, build_proc, NullStream())
        env_vars = {f"Key-{idx}": "v" * 100 for idx in range(100)}
        params = bpe._build_env_vars_params(env_vars)

        # 测试能通过参数反解出环境变量配置
        assert params["ENV_VARS_BLOCK_NUM"] == "5"
        encoded_str = "".join(params[f"ENV_VARS_BLOCK_{idx}"] for idx in range(int(params["ENV_VARS_BLOCK_NUM"])))
        assert json.loads(base64.b64decode(encoded_str).decode("utf-8")) == env_vars
