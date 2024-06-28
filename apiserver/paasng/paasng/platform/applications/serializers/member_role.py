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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.constants import ApplicationRole
from paasng.utils.serializers import UserField


class RoleField(serializers.Field):
    """Role field for present role object friendly"""

    def to_representation(self, value):
        return {"id": value, "name": ApplicationRole(value).name.lower()}

    def to_internal_value(self, data):
        try:
            role_id = data["id"]
        except Exception:
            raise ValidationError('Incorrect role param. Expected like {role: {"id": 3}}.')
        try:
            ApplicationRole(role_id)
        except Exception:
            raise ValidationError(_("%s 不是合法选项") % role_id)
        return role_id


class ApplicationMemberSLZ(serializers.Serializer):
    user = UserField()
    roles = serializers.ListField(child=RoleField(), help_text="用户角色列表")


class ApplicationMemberRoleOnlySLZ(serializers.Serializer):
    """Serializer for update, only role"""

    role = RoleField()
