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

import logging
from contextlib import contextmanager
from typing import Any, Dict, List

import cattrs
from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.infras.bcs import entities
from paasng.infras.bcs.apigw.client import Client
from paasng.infras.bcs.apigw.client import Group as BCSGroup
from paasng.infras.bcs.exceptions import BCSApiError, BCSGatewayServiceError

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except (APIGatewayResponseError, ResponseError) as e:
        raise BCSGatewayServiceError("call bcs api error, detail: {}".format(e))


class BCSClient:
    """BCS 通过 APIGW 提供的 API

    :param bk_username: 用户名
    :param stage: 网关环境
    """

    def __init__(self, bk_username: str, stage: str = "prod"):
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers({"X-Bcs-Username": bk_username})
        self.client: BCSGroup = client.api

    def list_projects(self) -> List[entities.Project]:
        """获取项目列表"""
        with wrap_request_exc():
            resp = self.client.list_auth_projects()
            self._validate_resp(resp)

        projects = cattrs.structure(resp["data"]["results"], List[entities.Project])
        # 只保留还没下线，且有绑定业务信息的项目
        return [p for p in projects if not p.isOffline and p.businessID and p.businessName]

    def list_clusters(self, project_id: str) -> List[entities.Cluster]:
        """获取集群列表"""
        path_params = {"projectID": project_id}

        with wrap_request_exc():
            resp = self.client.list_project_clusters(path_params=path_params)
            self._validate_resp(resp)

        clusters = cattrs.structure(resp["data"], List[entities.Cluster])
        # 只保留非共享集群
        return [c for c in clusters if not c.is_shared]

    @staticmethod
    def _validate_resp(resp: Dict[str, Any]):
        """Validate response status code"""
        if resp.get("code") == 0:
            return

        logger.error("call bcs api failed, resp: %s", resp)
        raise BCSApiError(resp["message"])
