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
import yaml
from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.infras.bcs import entities
from paasng.infras.bcs.apigw.client import Client
from paasng.infras.bcs.apigw.client import Group as BCSGroup
from paasng.infras.bcs.exceptions import BCSApiError, BCSGatewayServiceError, HelmChartNotFound

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except (APIGatewayResponseError, ResponseError) as e:
        raise BCSGatewayServiceError("call bcs api error, detail: {}".format(e))


class BCSClient:
    """BCS 通过 APIGW 提供的 API

    :param tenant_id: 租户 ID
    :param bk_username: 用户名
    :param stage: 网关环境
    """

    def __init__(self, tenant_id: str, bk_username: str, stage: str = "prod"):
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers(
            {
                API_HERDER_TENANT_ID: tenant_id,
                "X-Bcs-Username": bk_username,
            }
        )
        self.client: BCSGroup = client.api

    def list_auth_projects(self) -> List[entities.Project]:
        """获取有权限的项目列表"""
        with wrap_request_exc():
            resp = self.client.list_auth_projects()
            self._validate_resp(resp)

        projects = cattrs.structure(resp["data"]["results"], List[entities.Project])
        # 只保留还没下线，且有绑定业务信息的项目
        return [p for p in projects if not p.isOffline and p.businessID and p.businessName]

    def list_project_clusters(self, project_id: str) -> List[entities.Cluster]:
        """获取项目下的集群列表"""
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


class BCSUserClient:
    """BCS 通过 APIGW 提供的 API（用户态）"""

    def __init__(self, tenant_id: str, bk_username: str, credentials: str, stage: str = "prod"):
        """
        :param tenant_id: 租户 ID
        :param bk_username: 用户名
        :param credentials: 用户凭证（bk_ticket / bk_token）
        :param stage: 网关环境
        """
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        authorization = {
            "bk_app_code": settings.BK_APP_CODE,
            "bk_app_secret": settings.BK_APP_SECRET,
            "bk_username": bk_username,
            settings.BK_COOKIE_NAME: credentials,
        }
        client.update_bkapi_authorization(**authorization)
        client.update_headers(
            {
                API_HERDER_TENANT_ID: tenant_id,
                "X-Bcs-Username": bk_username,
            }
        )
        self.client: BCSGroup = client.api

    def get_chart_versions(self, project_id: str, repo_name: str, chart_name: str):
        path_params = {"projectCode": project_id, "repoName": repo_name, "name": chart_name}

        with wrap_request_exc():
            resp = self.client.get_chart_versions(path_params=path_params)
            self._validate_resp(resp)

        return cattrs.structure(resp["data"]["data"], List[entities.ChartVersion])

    def upgrade_release(
        self,
        project_id: str,
        cluster_id: str,
        namespace: str,
        release_name: str,
        repository: str,
        chart_name: str,
        chart_version: str,
        values: Dict[str, Any],
    ):
        """更新集群中的 helm release"""
        path_params = {
            # 已与 BCS 确认，ID / Code 都可以
            "projectCode": project_id,
            "clusterID": cluster_id,
            "namespace": namespace,
            "name": release_name,
        }

        data = {
            "repository": repository,
            "version": chart_version,
            "chart": chart_name,
            "values": [yaml.dump(values)],
        }
        with wrap_request_exc():
            resp = self.client.upgrade_release(path_params=path_params, data=data)
            self._validate_resp(resp)

    def upgrade_release_with_latest_chart_version(
        self,
        project_id: str,
        cluster_id: str,
        namespace: str,
        release_name: str,
        repository: str,
        chart_name: str,
        values: Dict[str, Any],
    ):
        """更新集群中的 helm release，使用最新的 chart 版本"""
        chart_versions = self.get_chart_versions(project_id, repository, chart_name)
        if not chart_versions:
            raise HelmChartNotFound(f"chart {chart_name} not found in repo {repository}")

        # API 返回是按时间逆序，因此第一个就是最新版本
        latest_version = chart_versions[0].version

        self.upgrade_release(
            project_id=project_id,
            cluster_id=cluster_id,
            namespace=namespace,
            release_name=release_name,
            repository=repository,
            chart_name=chart_name,
            chart_version=latest_version,
            values=values,
        )

    @staticmethod
    def _validate_resp(resp: Dict[str, Any]):
        """Validate response status code"""
        if resp.get("code") == 0:
            return

        logger.error("call bcs api failed, resp: %s", resp)
        raise BCSApiError(resp["message"])
