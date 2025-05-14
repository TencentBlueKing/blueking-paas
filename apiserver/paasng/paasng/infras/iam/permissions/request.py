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

from abc import ABC
from collections import namedtuple
from typing import Dict, List, Optional, Union

from django.conf import settings
from iam import Resource
from iam.apply import models


class ResourceRequest(ABC):
    resource_type = ""

    @classmethod
    def from_dict(cls, init_data: Dict) -> "ResourceRequest":
        """从字典构建对象"""
        raise NotImplementedError

    def make_resources(self, res_ids: Union[List[str], str]) -> List[Resource]:
        """
        :param res_ids: 单个资源 ID 或资源 ID 列表
        """
        if isinstance(res_ids, (str, int)):
            res_ids = [res_ids]

        res_ids = [str(_id) for _id in res_ids]

        return [
            Resource(settings.IAM_PAAS_V3_SYSTEM_ID, self.resource_type, _id, self._make_attribute(_id))
            for _id in res_ids
        ]

    def _make_attribute(self, res_id: str) -> Dict:
        return {}


IAMResource = namedtuple("IAMResource", "resource_type resource_id")


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
