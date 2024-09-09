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
from typing import List

from rest_framework import serializers

from paasng.core.region.states import RegionType
from paasng.platform.modules.constants import AppImageType, BuildPackType
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder
from paasng.utils.i18n.serializers import TranslatedCharField


class BuildPackCreateInputSLZ(serializers.ModelSerializer):
    region = serializers.ChoiceField(required=True, choices=RegionType.get_choices())
    name = serializers.CharField(required=True, max_length=64)
    language = serializers.CharField(required=True, max_length=32)
    type = serializers.ChoiceField(required=True, choices=BuildPackType.get_choices())
    address = serializers.CharField(required=True, max_length=2048)
    version = serializers.CharField(required=True, max_length=32)
    environments = serializers.JSONField(required=False, default={})
    is_hidden = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = AppBuildPack
        exclude = ["id", "created", "updated", "modules"]


class BuildPackUpdateInputSLZ(BuildPackCreateInputSLZ):
    pass


class BuildPackListOutputSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    environments = serializers.JSONField()

    class Meta:
        model = AppBuildPack
        exclude = ["modules"]


class AppSlugBuilderListOutputSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    environments = serializers.JSONField()
    labels = serializers.JSONField()

    class Meta:
        model = AppSlugBuilder
        exclude = ["modules"]


class BuildPackBindInputSLZ(serializers.Serializer):
    slugbuilder_id_list = serializers.ListField(child=serializers.CharField())

    def validate_slugbuilder_id_list(self, slugbuilder_id_list: List[str]) -> List[str]:
        for slugbuilder_id in slugbuilder_id_list:
            if not AppSlugBuilder.objects.filter(id=int(slugbuilder_id)).exists():
                raise serializers.ValidationError(f"slug builder {slugbuilder_id} not exists")
            builder_type = AppSlugBuilder.objects.get(id=int(slugbuilder_id)).type

            # TAR 类型的 BuildPack 只能绑定 legacy 类型 slugbuilder，OCI 类型 BuildPack 只能绑定 cnb 类型 slugbuilder
            if (builder_type == AppImageType.CNB and self.context["buildpack_type"] == BuildPackType.TAR) or (
                builder_type == AppImageType.LEGACY and self.context["buildpack_type"] != BuildPackType.TAR
            ):
                raise serializers.ValidationError(f"builder {slugbuilder_id}: does not match buildpack type")

        return slugbuilder_id_list
