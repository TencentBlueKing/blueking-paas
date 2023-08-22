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
from typing import Optional

from attrs import define

from paasng.accessories.bkmonitorv3.constants import SpaceType
from paasng.platform.applications.models import Application


@define
class BkMonitorSpace:
    """蓝鲸监控空间定义

    :param space_type_id: 空间类型id, 枚举范围见 SpaceType
    :param space_id: 空间id, 同一 space_type_id 范围内唯一, 对于 bksaas 类型的空间, space_id 即 app_code
    :param space_name: 空间名称, 对于 bksaas 类型的空间, space_name 即 app_name
    :param creator: 空间 creator

    :param id: 纯数字的 ID, 不同于 space_id.
    :param space_uid: 全局唯一的 uid, 拼接规则: `${space_type_id}__${space_id}`
    :param extra_info: 蓝鲸监控API - metadata_create_space/metadata_update_space/metadata_get_space_detail
                       的原始返回值, 包含其他未被使用的空间相关的属性
    """

    space_type_id: SpaceType
    space_id: str
    space_name: str
    creator: str

    # 真正创建后才会赋值
    id: Optional[int] = None
    space_uid: Optional[str] = None
    extra_info: Optional[dict] = None

    @property
    def iam_resource_id(self) -> str:
        """蓝鲸监控空间在权限中心的 资源id

        对于非 bkcc 类型的空间, 目前在 权限中心注册的 资源id 是取 空间id 的负数
        """
        if self.space_type_id != SpaceType.BKCC:
            return f"-{self.id}"
        # TODO: 确认 bkcc 类型的空间在权限中心的 资源id 是否等于 空间id
        return f"{self.id}"


def gen_bk_monitor_space(application: Application) -> BkMonitorSpace:
    """生成蓝鲸监控空间定义"""
    return BkMonitorSpace(
        space_type_id=SpaceType.SAAS,
        space_id=application.code,
        space_name=application.name,
        creator=application.creator.username,
    )
