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
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.utils.i18n.serializers import TranslatedCharField


class BuildPackCreateInputSLZ(serializers.ModelSerializer):
    region = serializers.ChoiceField(required=True, choices=RegionType.get_choices())
    name = serializers.CharField(required=True, max_length=64)
    language = serializers.CharField(required=True, max_length=32)
    type = serializers.ChoiceField(required=True, choices=BuildPackType.get_choices())
    address = serializers.CharField(required=True, max_length=2048)
    version = serializers.CharField(required=True, max_length=32)
    env_vars = serializers.JSONField(required=False, default={}, source="environments", help_text="环境变量")
    is_hidden = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = AppBuildPack
        exclude = ["id", "created", "updated", "modules", "environments"]


class BuildPackUpdateInputSLZ(BuildPackCreateInputSLZ):
    pass


class BuildPackListOutputSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    env_vars = serializers.JSONField(source="environments", help_text="环境变量")

    class Meta:
        model = AppBuildPack
        exclude = ["modules", "environments"]


class BuildPackBindInputSLZ(serializers.Serializer):
    """用于给单个 Buildpack 绑定 slugbuilder 列表，需要传入 context["buildpack_type"] 用于验证 slugbuilder 类型"""

    slugbuilder_ids = serializers.ListField(child=serializers.CharField())

    def validate_slugbuilder_ids(self, slugbuilder_ids: List[str]) -> List[str]:
        builder_types = {sb.type for sb in AppSlugBuilder.objects.filter(id__in=slugbuilder_ids)}

        # TAR 类型的 BuildPack 只能绑定 legacy 类型 slugbuilder，OCI 类型 BuildPack 只能绑定 cnb 类型 slugbuilder
        buildpack_builder_type_map = BuildPackType.get_buildpack_builder_type_map()
        for builder_type in builder_types:
            if builder_type != buildpack_builder_type_map[self.context["buildpack_type"]]:
                raise serializers.ValidationError(f"builder type ({builder_type}): does not match buildpack type")

        return slugbuilder_ids


class AppSlugBuilderCreateInputSLZ(serializers.ModelSerializer):
    region = serializers.ChoiceField(required=True, choices=RegionType.get_choices())
    name = serializers.CharField(required=True, max_length=64)
    type = serializers.ChoiceField(required=True, choices=AppImageType.get_choices())
    image = serializers.CharField(required=True, max_length=256)
    tag = serializers.CharField(required=True, max_length=32)
    env_vars = serializers.JSONField(required=False, default={}, source="environments", help_text="环境变量")
    labels = serializers.JSONField(required=False, default={})
    is_hidden = serializers.BooleanField(required=False, default=False)
    is_default = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = AppSlugBuilder
        exclude = ["id", "created", "updated", "modules", "environments", "buildpacks"]

    def validate_name(self, name: str) -> str:
        if AppSlugBuilder.objects.filter(name=name).exists():
            raise serializers.ValidationError("name already exists")
        return name


class AppSlugBuilderUpdateInputSLZ(AppSlugBuilderCreateInputSLZ):
    def validate_name(self, name: str) -> str:
        if AppSlugBuilder.objects.exclude(id=self.instance.id).filter(name=name).exists():
            raise serializers.ValidationError("name already exists")
        return name


class AppSlugBuilderListOutputSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    env_vars = serializers.JSONField(source="environments", help_text="环境变量")
    labels = serializers.JSONField()

    class Meta:
        model = AppSlugBuilder
        exclude = ["modules", "environments"]


class AppSlugBuilderBindInputSLZ(serializers.Serializer):
    """用于给 slugbuilder 绑定 buildpack 列表，需要传入 context["slugbuilder_type"] 用于验证 buildpack 类型"""

    buildpack_ids = serializers.ListField(child=serializers.CharField())

    def validate_buildpack_ids(self, buildpack_ids: List[str]) -> List[str]:
        buildpack_types = {bp.type for bp in AppBuildPack.objects.filter(id__in=buildpack_ids)}

        # TAR 类型的 BuildPack 只能绑定 legacy 类型 slugbuilder，OCI 类型 BuildPack 只能绑定 cnb 类型 slugbuilder
        buildpack_builder_type_map = BuildPackType.get_buildpack_builder_type_map()
        for buildpack_type in buildpack_types:
            if self.context["slugbuilder_type"] != buildpack_builder_type_map[buildpack_type]:
                raise serializers.ValidationError(
                    f"buildpack type ({buildpack_type}): does not match slugbuilder type"
                )

        return buildpack_ids


class AppSlugRunnerListOutputSLZ(serializers.ModelSerializer):
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    env_vars = serializers.JSONField(source="environments", help_text="环境变量")
    labels = serializers.JSONField()

    class Meta:
        model = AppSlugRunner
        exclude = ["modules", "environments"]


class AppSlugRunnerCreateInputSLZ(serializers.ModelSerializer):
    region = serializers.ChoiceField(required=True, choices=RegionType.get_choices())
    name = serializers.CharField(required=True, max_length=64)
    type = serializers.ChoiceField(required=True, choices=AppImageType.get_choices())
    image = serializers.CharField(required=True, max_length=256)
    tag = serializers.CharField(required=True, max_length=32)
    env_vars = serializers.JSONField(required=False, default={}, source="environments", help_text="环境变量")
    labels = serializers.JSONField(required=False, default={})
    is_hidden = serializers.BooleanField(required=False, default=False)
    is_default = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = AppSlugRunner
        exclude = ["modules", "id", "created", "updated", "environments"]

    def validate_name(self, name: str) -> str:
        if AppSlugBuilder.objects.filter(name=name).exists():
            raise serializers.ValidationError("name already exists")
        return name


class AppSlugRunnerUpdateInputSLZ(AppSlugRunnerCreateInputSLZ):
    def validate_name(self, name: str) -> str:
        if AppSlugBuilder.objects.exclude(id=self.instance.id).filter(name=name).exists():
            raise serializers.ValidationError("name already exists")
        return name
