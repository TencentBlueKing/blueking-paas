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
    """蓝鲸监控空间定义"""

    space_type_id: str
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
        creator=application.creator,
    )
