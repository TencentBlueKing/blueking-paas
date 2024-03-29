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
import logging
from contextlib import contextmanager
from typing import Any, Dict

import cattrs
from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.infras.bk_ci import entities
from paasng.infras.bk_ci.apigw.client import Client
from paasng.infras.bk_ci.apigw.client import Group as BkDevopsGroup
from paasng.infras.bk_ci.exceptions import BkCIApiError, BkCIGatewayServiceError

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except (APIGatewayResponseError, ResponseError) as e:
        raise BkCIGatewayServiceError("call bk ci api error, detail: {}".format(e))


class BaseBkCIClient:
    """bk-devops 通过 APIGW 提供的 API

    :param bk_username: 用户名
    :param stage: 网关环境, 蓝盾只提供了正式环境(prod)的 API
    """

    def __init__(self, bk_username: str, stage: str = "prod"):
        self.bk_username = bk_username

        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers(self._prepare_headers())
        self.client: BkDevopsGroup = client.api

    def _prepare_headers(self) -> dict:
        # 应用态 API 需要添加 X-DEVOPS-UID，用户态 API 不需要
        return {"X-DEVOPS-UID": self.bk_username}


class BkCIPipelineClient(BaseBkCIClient):
    """bk-devops pipeline 控制器"""

    def start_build(self, pipeline: entities.Pipeline, start_params: Dict[str, str]) -> entities.PipelineBuild:
        """启动构建

        :param pipeline: 流水线对象
        :param start_params: 启动参数：Dict<变量名(string),变量值(string)>
        """
        path_params = {"projectId": pipeline.projectId}
        query_params = {"pipelineId": pipeline.pipelineId}

        with wrap_request_exc():
            resp = self.client.v4_app_build_start(path_params=path_params, params=query_params, data=start_params)
            self._validate_resp(resp)

        data = resp["data"]
        return cattrs.structure(data, entities.PipelineBuild)

    def retrieve_build_detail(self, build: entities.PipelineBuild) -> entities.PipelineBuildDetail:
        """查询构建详情

        :param build: 流水线构建对象
        """
        path_params = {"projectId": build.projectId}
        query_params = {"pipelineId": build.pipelineId, "buildId": build.buildId}

        with wrap_request_exc():
            resp = self.client.v4_app_build_detail(path_params=path_params, params=query_params)
            self._validate_resp(resp)

        data = resp["data"]
        return cattrs.structure(data, entities.PipelineBuildDetail)

    def retrieve_build_status(self, build: entities.PipelineBuild) -> entities.PipelineBuildStatus:
        """查询构建状态信息

        :param build: 流水线构建对象
        """
        path_params = {"projectId": build.projectId}
        query_params = {"pipelineId": build.pipelineId, "buildId": build.buildId}

        with wrap_request_exc():
            resp = self.client.v4_app_build_status(path_params=path_params, params=query_params)
            self._validate_resp(resp)

        data = resp["data"]
        return cattrs.structure(data, entities.PipelineBuildStatus)

    def stop_build(self, build: entities.PipelineBuild) -> bool:
        """停止构建

        :param build: 流水线构建对象
        """
        path_params = {"projectId": build.projectId}
        query_params = {"pipelineId": build.pipelineId, "buildId": build.buildId}

        with wrap_request_exc():
            resp = self.client.v4_app_build_stop(path_params=path_params, params=query_params)
            self._validate_resp(resp)

        return resp["data"]

    def retrieve_full_log(self, build: entities.PipelineBuild) -> entities.PipelineLogModel:
        """查询全量日志

        :param build: 流水线构建对象
        """
        log_num = self._retrieve_log_num(build)
        return self._retrieve_log(build, start=0, num=log_num)

    def _retrieve_log(self, build: entities.PipelineBuild, start: int, num: int = 500) -> entities.PipelineLogModel:
        """查询日志

        :param build: 流水线构建对象
        :param start: 起始行号
        :param num: 日志行数
        """
        path_params = {"projectId": build.projectId}
        query_params = {
            "pipelineId": build.pipelineId,
            "buildId": build.buildId,
            "start": start,
            "end": start + num,
            "num": num,
        }

        with wrap_request_exc():
            resp = self.client.v4_app_log_more(path_params=path_params, params=query_params)
            self._validate_resp(resp)

        data = resp["data"]
        return cattrs.structure(data, entities.PipelineLogModel)

    def _retrieve_log_num(self, build: entities.PipelineBuild) -> int:
        """查询流水线步骤的日志总数"""
        path_params = {"projectId": build.projectId}
        query_params = {"pipelineId": build.pipelineId, "buildId": build.buildId}

        with wrap_request_exc():
            resp = self.client.v4_app_log_line_num(path_params=path_params, params=query_params)
            self._validate_resp(resp)

        data = resp["data"]
        return data["lastLineNum"]

    @staticmethod
    def _validate_resp(resp: Dict[str, Any]):
        """Validate response status code"""
        if resp.get("status") == 0:
            return

        logger.error("call bk ci api failed, resp: %s", resp)
        raise BkCIApiError(resp["message"])
