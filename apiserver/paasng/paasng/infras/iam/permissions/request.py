# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from abc import ABC
from typing import Dict, List, NamedTuple, Optional, Union

from django.conf import settings
from iam.apply import models

from paasng.infras.iam.base.dto import AuthResource
from paasng.infras.iam.shim import get_paas_system_id


class ResourceRequest(ABC):  # noqa: B024
    resource_type = ""

    @classmethod
    def from_dict(cls, init_data: Dict) -> "ResourceRequest":
        """从字典构建对象"""
        raise NotImplementedError

    def make_resource(self, res_id: str) -> AuthResource:
        """构造鉴权用的资源实例

        :param res_id: 单个资源实例 ID
        """
        return AuthResource(get_paas_system_id(), self.resource_type, res_id, self._make_attribute(res_id))

    def _make_attribute(self, res_id: str) -> Dict:
        return {}


class IAMResource(NamedTuple):
    resource_type: str
    resource_id: str


class ActionResourcesRequest:
    """操作资源请求"""

    def __init__(
        self,
        action_id: str,
        resource_type: Optional[str] = None,
        resources: Optional[List[str]] = None,
    ):
        """
        :param action_id: 操作 ID
        :param resource_type: 资源类型
        :param resources: 资源 ID 列表. 为 None 时, 表示资源无关; 资源实例相关时, resources 表示的资源必须具有相同的父实例.
        """
        self.action_id = action_id
        self.resource_type = resource_type
        self.resources = resources

    def to_action(self) -> Union[models.ActionWithResources, models.ActionWithoutResources]:
        # 资源实例相关
        if self.resources:
            instances = [
                models.ResourceInstance([models.ResourceNode(self.resource_type, res_id, res_id)])
                for res_id in self.resources
            ]
            related_resource_type = models.RelatedResourceType(
                settings.IAM_PAAS_V3_SYSTEM_ID, self.resource_type, instances
            )
            return models.ActionWithResources(self.action_id, [related_resource_type])

        # 资源实例无关
        return models.ActionWithoutResources(self.action_id)
