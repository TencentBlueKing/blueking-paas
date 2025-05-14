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

from typing import Any, Dict, List

from paasng.infras.bcs.entities import ChartVersion


class StubBCSUserClient:
    """BCS 用户态 API 客户端（仅供单元测试使用）"""

    def __init__(self, *args, **kwargs): ...

    def get_chart_versions(self, project_id: str, repo_name: str, chart_name: str) -> List[ChartVersion]:
        """获取 Chart 的可用版本（按时间逆序）"""
        return [
            ChartVersion(name=chart_name, version="3.0.0", appVersion="v3.0.0"),
            ChartVersion(name=chart_name, version="2.0.0", appVersion="v2.0.0"),
            ChartVersion(name=chart_name, version="1.0.0", appVersion="v1.0.0"),
        ]

    def upgrade_release(self, *args, **kwargs):
        """更新集群中的 helm release"""

    def upgrade_release_to_latest_chart_version(
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
        chart_versions = self.get_chart_versions("", "", chart_name)

        # API 返回是按时间逆序，因此第一个就是最新版本
        self.upgrade_release(chart_versions[0].version)
