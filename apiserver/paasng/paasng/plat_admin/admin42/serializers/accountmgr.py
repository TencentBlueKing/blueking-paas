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

import logging

from bkpaas_auth.core.constants import ProviderType
from rest_framework import serializers

from paasng.infras.accounts.constants import SiteRole
from paasng.utils.serializers import UserField

PROVIDER_TYPE_CHCOISE = (
    (ProviderType.UIN.value, "UIN"),
    (ProviderType.RTX.value, "RTX"),
    (ProviderType.BK.value, "BK"),
    (ProviderType.DATABASE.value, "DATABASE"),
)
logger = logging.getLogger(__name__)


class UserProfileBulkCreateFormSLZ(serializers.Serializer):
    role = serializers.ChoiceField(choices=SiteRole.get_choices())
    provider_type = serializers.ChoiceField(choices=PROVIDER_TYPE_CHCOISE)
    username_list = serializers.ListField(child=serializers.CharField())
    enable_regions = serializers.ListField(child=serializers.CharField(), default=None, min_length=1)


class UserProfileUpdateFormSLZ(serializers.Serializer):
    role = serializers.ChoiceField(choices=SiteRole.get_choices())
    enable_regions = serializers.ListField(child=serializers.CharField(), default=None, min_length=1)
    user = UserField()


class UserProfileQueryParamSLZ(serializers.Serializer):
    display_regular_users = serializers.BooleanField(default=False, required=False)
    filter_key = serializers.CharField(default=None, required=False, allow_null=True)


class UserProfileSLZ(serializers.Serializer):
    user = UserField()
    role = serializers.ChoiceField(choices=SiteRole.get_choices())
    updated = serializers.DateTimeField(read_only=True)
    enable_regions = serializers.SerializerMethodField()

    def get_enable_regions(self, value):
        return [region.name for region in value.enable_regions]
