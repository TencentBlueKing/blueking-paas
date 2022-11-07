# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
from abc import ABC
from typing import Dict, List, Type, Union

from attrs import asdict, define, field, validators
from django.conf import settings

from paasng.accessories.iam.constants import ResourceType

from .client import IAMClient
from .exceptions import AttrValidationError, PermissionDeniedError
from .request import ActionResourcesRequest, ResourceRequest

logger = logging.getLogger(__name__)


def validate_empty(instance, attribute, value):
    """用于校验属性是否为空. https://www.attrs.org/en/20.2.0/init.html#callables"""
    if not value:
        raise AttrValidationError(f"{attribute.name} must not be empty")


@define
class ResCreatorAction:
    """用于新建关联属性授权接口"""

    creator: str
    resource_type: ResourceType
    system: str = field(init=False)

    def __attrs_post_init__(self):
        self.system = settings.IAM_PAAS_V3_SYSTEM_ID

    def to_data(self) -> Dict:
        return {'creator': self.creator, 'system': self.system, 'type': self.resource_type}


@define(kw_only=True)
class PermCtx:
    """
    权限参数上下文
    note: 由于 force_raise 默认值的原因，其子类属性必须设置默认值
    """

    username = field(validator=[validators.instance_of(str), validate_empty])
    # 如果为 True, 表示不做权限校验，直接以无权限方式抛出异常
    force_raise = field(validator=[validators.instance_of(bool)], default=False)

    def validate_resource_id(self):
        """校验资源实例 ID. 如果校验不过，抛出 AttrValidationError 异常"""
        if not self.resource_id:
            raise AttrValidationError('resource_id required!')

    @property
    def resource_id(self) -> str:
        """注册到权限中心的资源实例 ID. 空字符串表示实例无关"""
        return ''


class Permission(ABC, IAMClient):
    """对接 IAM 的权限基类"""

    resource_type: str = ''
    resource_request_cls: Type[ResourceRequest] = ResourceRequest

    def can_action(self, perm_ctx: PermCtx, action_id: str, raise_exception: bool, use_cache: bool = False) -> bool:
        """
        校验用户的 action_id 权限

        :param perm_ctx: 权限校验的上下文
        :param action_id: 资源操作 ID
        :param raise_exception: 无权限时，是否抛出异常
        :param use_cache: 是否使用本地缓存 (缓存时间 1 min) 校验权限。用于非敏感操作鉴权，比如 view 操作
        """
        if perm_ctx.force_raise:
            self._raise_permission_denied_error(perm_ctx, action_id)

        is_allowed = self._can_action(perm_ctx, action_id, use_cache)

        if raise_exception and not is_allowed:
            self._raise_permission_denied_error(perm_ctx, action_id)

        return is_allowed

    def can_multi_actions(self, perm_ctx: PermCtx, action_ids: List[str], raise_exception: bool) -> bool:
        """
        校验同类型单个资源的多个 action 权限

        :param perm_ctx: 权限校验的上下文
        :param action_ids: 资源 action_id 列表
        :param raise_exception: 无权限时，是否抛出异常
        :returns: 只有 action_ids 都有权限时，才返回 True; 否则返回 False 或者抛出异常
        """
        perm_ctx.validate_resource_id()

        # perms 结构如 {'view_basic_info': True, 'edit_basic_info': False}
        if perm_ctx.force_raise:
            perms = {action_id: False for action_id in action_ids}
        else:
            res_request = self.make_res_request(perm_ctx)
            perms = self.resource_inst_multi_actions_allowed(
                perm_ctx.username, action_ids, resources=res_request.make_resources(perm_ctx.resource_id)
            )

        return self._can_multi_actions(perm_ctx, perms, raise_exception)

    def resources_actions_allowed(
        self, username: str, action_ids: List[str], res_ids: Union[List[str], str], res_request: ResourceRequest
    ):
        """
        判断用户对某些资源是否具有多个指定操作的权限. 当前 sdk 仅支持同类型的资源
        :returns: 示例 {'app_code_test': {'view_basic_info': True, 'edit_basic_info': False}}
        """

        return self.batch_resource_multi_actions_allowed(username, action_ids, res_request.make_resources(res_ids))

    def grant_resource_creator_actions(self, creator_action: ResCreatorAction):
        """
        用于创建资源时，注册用户对该资源的关联操作权限.
        note: 具体的关联操作见权限模型的 resource_creator_actions 字段
        """
        return self.iam._client.grant_resource_creator_actions(None, creator_action.creator, creator_action.to_data())

    def make_res_request(self, perm_ctx: PermCtx) -> ResourceRequest:
        return self.resource_request_cls.from_dict(asdict(perm_ctx))

    def _can_action(self, perm_ctx: PermCtx, action_id: str, use_cache: bool = False) -> bool:
        res_id = perm_ctx.resource_id

        if not res_id:
            # 与资源实例无关
            return self.resource_type_allowed(perm_ctx.username, action_id, use_cache)

        # 与当前资源实例相关
        res_request = self.make_res_request(perm_ctx)
        resources = res_request.make_resources(res_id)
        return self.resource_inst_allowed(perm_ctx.username, action_id, resources, use_cache)

    def _can_multi_actions(self, perm_ctx: PermCtx, perms: Dict[str, bool], raise_exception: bool) -> bool:
        messages = []
        action_request_list = []

        for action_id, is_allowed in perms.items():
            if is_allowed:
                continue

            try:
                self._raise_permission_denied_error(perm_ctx, action_id)
            except PermissionDeniedError as e:
                messages.append(e.message)
                action_request_list.extend(e.action_request_list)

        if not messages:
            return True

        if not raise_exception:
            return False

        raise PermissionDeniedError(
            message=';'.join(messages), username=perm_ctx.username, action_request_list=action_request_list
        )

    def _raise_permission_denied_error(self, perm_ctx: PermCtx, action_id: str):
        """抛出 PermissionDeniedError 异常, 其中 username 和 action_request_list 可用于生成权限申请跳转链接"""
        resources = [perm_ctx.resource_id] if perm_ctx.resource_id else None

        raise PermissionDeniedError(
            f"no {action_id} permission",
            username=perm_ctx.username,
            action_request_list=[ActionResourcesRequest(action_id, self.resource_type, resources)],
        )
