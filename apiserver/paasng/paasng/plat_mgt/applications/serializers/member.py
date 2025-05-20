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


from rest_framework import serializers

from paasng.platform.applications.serializers.member_role import RoleField
from paasng.utils.serializers import UserField


class ApplicationMembershipListOutputSLZ(serializers.Serializer):
    """平台管理 - 应用成员序列化器"""

    user = UserField()
    roles = serializers.ListField(child=RoleField(), help_text="用户角色列表")


class ApplicationMembershipCreateInputSLZ(serializers.Serializer):
    """平台管理 - 创建应用成员序列化器"""

    users = serializers.ListField(child=UserField(), help_text="用户列表")
    role = RoleField(help_text="用户角色")


class ApplicationMembershipUpdateInputSLZ(serializers.Serializer):
    """平台管理 - 修改应用成员序列化器"""

    role = RoleField(help_text="用户角色")
