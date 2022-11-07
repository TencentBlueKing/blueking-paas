# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
"""用户组织架构相关
"""
from dataclasses import dataclass

from paasng.accessories.bk_components.tof import (
    ComponentResponseInvalid,
    get_center_info_by_groupid,
    tof_get_bg_info_by_dept_id,
    tof_get_staff_info,
)


@dataclass
class UserOrganization:
    chinese_name: str = ""
    status_name: str = ""
    type_name: str = ""
    bg_name: str = ""
    dept_name: str = ""
    center_name: str = ""
    group_name: str = ""


def get_user_organization(username):

    try:
        # tof 获取用户信息的函数已经添加了缓存
        staff_info = tof_get_staff_info(username)
        center_info = get_center_info_by_groupid(staff_info['GroupId'])
    except ComponentResponseInvalid:
        return UserOrganization()

    dept_id, dept_name = int(staff_info["DepartmentId"]), staff_info["DepartmentName"]
    bg_id, bg_name = tof_get_bg_info_by_dept_id(dept_id, dept_name)
    return UserOrganization(
        staff_info['ChineseName'],
        staff_info['StatusName'],
        staff_info['TypeName'],
        bg_name,
        staff_info['DepartmentName'],
        center_info.get('CenterName', ''),
        staff_info['GroupName'],
    )
