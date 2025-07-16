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

from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from iam import IAM, Action, MultiActionRequest, Request, Resource, Subject

from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import PluginPermissionActions
from paasng.bk_plugins.pluginscenter.iam_adaptor.definitions import IAMResource
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.converter import PluginPolicyConverter


class BKIAMClient:
    """bk-iam 通过 SDK 提供的 API client"""

    def __init__(self, tenant_id: str):
        self._iam = IAM(
            settings.IAM_APP_CODE,
            settings.IAM_APP_SECRET,
            settings.BK_IAM_APIGATEWAY_URL,
            bk_tenant_id=tenant_id,
        )
        self.tenant_id = tenant_id

    def is_action_allowed(
        self,
        username: str,
        action: PluginPermissionActions,
        resources: Optional[List[IAMResource]] = None,
        use_cache: bool = False,
    ) -> bool:
        """判断用户是否具备某个操作的权限"""
        sdk_resources = [
            Resource(
                system=settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                type=resource.resource_type,
                id=resource.id,
                attribute=resource.iam_attribute,
            )
            for resource in resources or []
        ]
        request = Request(
            settings.IAM_PLUGINS_CENTER_SYSTEM_ID, Subject("user", username), Action(action), sdk_resources, None
        )

        if use_cache:
            return self._iam.is_allowed_with_cache(request)
        return self._iam.is_allowed(request)

    def is_actions_allowed(
        self,
        username: str,
        actions: List[PluginPermissionActions],
        resources: Optional[List[IAMResource]] = None,
    ) -> Dict[str, bool]:
        """
        判断用户对某个(单个)资源实例是否具有多个操作的权限.
        note: 权限判断与资源实例有关，如更新某个具体资源

        :returns: Dict[action_id, bool]
        """
        sdk_actions = [Action(action_id) for action_id in actions]
        sdk_resources = [
            Resource(
                system=settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                type=resource.resource_type,
                id=resource.id,
                attribute=resource.iam_attribute,
            )
            for resource in resources or []
        ]
        request = MultiActionRequest(
            settings.IAM_PLUGINS_CENTER_SYSTEM_ID, Subject("user", username), sdk_actions, sdk_resources, None
        )
        return self._iam.resource_multi_actions_allowed(request)

    def is_batch_resource_actions_allowed(
        self,
        username: str,
        actions: List[PluginPermissionActions],
        resources_list: List[List[Resource]],
    ) -> Dict[str, Dict[str, bool]]:
        """
        判断用户对多个资源组合是否具有多个指定操作的权限. 当前sdk仅支持同类型的资源

        :returns: Dict[resource_id, Dict[action_id, bool]]
        """
        sdk_actions = [Action(action_id) for action_id in actions]
        sdk_resources_list = [
            [
                Resource(
                    system=settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                    type=resource.resource_type,
                    id=resource.id,
                    attribute=resource.iam_attribute,
                )
                for resource in resources
            ]
            for resources in resources_list or []
        ]
        # NOTE: batch_resource_multi_actions_allowed 构建的 requests 请求不需要传 resources
        request = MultiActionRequest(
            settings.IAM_PLUGINS_CENTER_SYSTEM_ID, Subject("user", username), sdk_actions, [], None
        )
        return self._iam.batch_resource_multi_actions_allowed(request, sdk_resources_list)

    def build_plugin_filters(self, username: str) -> Q:
        """用户有基础开发权限的插件列表"""
        request = Request(
            settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
            Subject("user", username),
            Action(PluginPermissionActions.BASIC_DEVELOPMENT),
            [],
            None,
        )
        filters = self._iam.make_filter(request, converter_class=PluginPolicyConverter)
        if not filters:
            return filters

        # 过滤掉非当前租户的插件
        return filters & Q(tenant_id=self.tenant_id)
