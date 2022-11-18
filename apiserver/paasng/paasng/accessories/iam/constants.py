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
from blue_krill.data_types.enum import StructuredEnum

from paasng.platform.applications.constants import ApplicationRole

# 使用 -1 表示永不过期
NEVER_EXPIRE_DAYS = -1

# 永不过期的时间（伪，其实是 2100.01.01 08:00:00，与权限中心保持一致)
NEVER_EXPIRE_TIMESTAMP = 4102444800

# 每一天的秒数
ONE_DAY_SECONDS = 24 * 60 * 60

# 默认为每个 APP 创建 3 个用户组，分别是管理者，开发者，运营者
APP_DEFAULT_ROLES = [ApplicationRole.ADMINISTRATOR, ApplicationRole.DEVELOPER, ApplicationRole.OPERATOR]

# 默认从第一页查询
DEFAULT_PAGE = 1

# 查询用户组成员，全量查询
FETCH_USER_GROUP_MEMBERS_LIMIT = 10000


class ResourceType(str, StructuredEnum):
    Application = 'application'
