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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, PersistentStorageSize, VolumeSourceType
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError
from paas_wl.bk_app.cnative.specs.mounts import init_volume_source_controller

from .models import AppModelRevision, ConfigMapSource, Mount, PersistentStorageSource

logger = logging.getLogger(__name__)


class AppModelRevisionSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelRevision object"""

    class Meta:
        model = AppModelRevision
        exclude = ("module_id", "yaml_value")


class ResourceQuotaSLZ(serializers.Serializer):
    cpu = serializers.CharField()
    memory = serializers.CharField()


class ResQuotaPlanSLZ(serializers.Serializer):
    """Serializer for ResQuotaPlan option"""

    name = serializers.CharField(help_text="选项名称")
    value = serializers.CharField(help_text="选项值")
    request = ResourceQuotaSLZ(help_text="资源请求")
    limit = ResourceQuotaSLZ(help_text="资源限制")


class ConfigMapSLZ(serializers.Serializer):
    source_config_data = serializers.DictField(
        help_text=_(
            "挂载卷内容为一个字典，其中键表示文件名称，值表示文件内容。"
            "例如：{'file1.yaml': 'file1 content', 'file2.yaml': 'file2 content'}"
        ),
        child=serializers.CharField(),
        allow_null=True,
    )

    def validate_source_config_data(self, data):
        if not data:
            return None
        for key in data:
            if not key:
                raise serializers.ValidationError("key cannot be empty")
        return data


class PersistentStorageSLZ(serializers.Serializer):
    storage_size = serializers.ChoiceField(choices=PersistentStorageSize.get_choices(), allow_null=True)


class UpsertMountSLZ(serializers.Serializer):
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=True)
    name = serializers.RegexField(
        help_text=_("挂载卷名称"), regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63, required=True
    )
    # 该正则匹配以'/'开头，不包含空字符(\0)和连续'/'的文件路径，且根目录'/'不合法
    # 合法路径：/xxx/ 和 /xxx  非法路径：/ 和 /xxx//
    mount_path = serializers.RegexField(regex=r"^/([^/\0]+(/)?)+$", required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)
    # TODO: 更改为 resource_name 更合适
    source_name = serializers.CharField(help_text="共享挂载资源的名称", allow_blank=True, required=False)
    configmap_source = ConfigMapSLZ(required=False, allow_null=True)
    persistent_storage_source = PersistentStorageSLZ(required=False, allow_null=True)
    sub_paths = serializers.ListField(child=serializers.CharField(), help_text="子路径列表")

    def validate(self, attrs):
        environment_name = attrs["environment_name"]
        name = attrs["name"]

        module_id = self.context.get("module_id")

        # 验证重名挂载卷
        filtered_mounts = Mount.objects.filter(
            module_id=module_id,
            name=name,
            environment_name__in=[environment_name, MountEnvName.GLOBAL.value],
        )
        # 传入了 mount_instance 表示更新操作，否则表示创建操作。更新操作时候，排除被更新 mount 对象
        if mount_id := self.context.get("mount_id", None):
            filtered_mounts = filtered_mounts.exclude(id=mount_id)

        if filtered_mounts.exists():
            raise serializers.ValidationError(_("该环境(包括 global )中已存在同名挂载卷"))

        # 根据 source_type 验证 source_config_data
        source_type = attrs["source_type"]
        configmap_source = attrs.get("configmap_source") or {}
        if source_type == VolumeSourceType.ConfigMap.value and not configmap_source.get("source_config_data"):
            raise serializers.ValidationError(_("挂载卷内容不可为空"))
        return attrs


class MountSLZ(serializers.ModelSerializer):
    configmap_source = serializers.SerializerMethodField(label=_("configmap 挂载"))
    persistent_storage_source = serializers.SerializerMethodField(label=_("持久存储资源"))

    class Meta:
        model = Mount
        fields = (
            "id",
            "created",
            "updated",
            "module_id",
            "environment_name",
            "name",
            "mount_path",
            "source_type",
            "source_config",
            "configmap_source",
            "persistent_storage_source",
        )

    def get_configmap_source(self, obj):
        if obj.source_type != VolumeSourceType.ConfigMap.value:
            return None
        try:
            controller = init_volume_source_controller(obj.source_type)
            source = controller.get_by_env(
                app_id=obj.module.application.id,
                env_name=obj.environment_name,
                source_name=obj.get_source_name,
            )
        except ValueError as e:
            raise GetSourceConfigDataError(_("获取挂载卷内容信息失败")) from e
        return {"source_config_data": source.data}

    def get_persistent_storage_source(self, obj):
        if obj.source_type != VolumeSourceType.PersistentStorage.value:
            return None
        try:
            controller = init_volume_source_controller(obj.source_type)
            source = controller.get_by_env(
                app_id=obj.module.application.id,
                env_name=obj.environment_name,
                source_name=obj.get_source_name,
            )
        except ValueError as e:
            raise GetSourceConfigDataError(_("获取挂载卷内容信息失败")) from e

        mounts = Mount.objects.filter(
            source_config=controller.build_volume_source(source.name),
        )
        bound_modules = [{"module": mount.module.name, "path": mount.mount_path} for mount in mounts]
        return {
            "name": source.name,
            "storage_size": source.storage_size,
            "bound_modules": bound_modules,
            "display_name": source.display_name,
        }


class QueryMountsSLZ(serializers.Serializer):
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=False)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=False)


class QueryMountSourcesSLZ(serializers.Serializer):
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=False)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)


class CreateMountSourceSLZ(serializers.Serializer):
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)
    configmap_source = ConfigMapSLZ(required=False, allow_null=True)
    persistent_storage_source = PersistentStorageSLZ(required=False, allow_null=True)
    display_name = serializers.CharField(max_length=63, required=False)

    def validate(self, attrs):
        environment_name = attrs["environment_name"]
        storage_size = attrs.get("persistent_storage_source", {}).get("storage_size")

        if storage_size != PersistentStorageSize.P_1G.value and environment_name == MountEnvName.STAG.value:
            raise serializers.ValidationError("预发布环境仅支持 1G 的持久存储")

        # 检查挂载资源 display_name 是否存在
        display_name = attrs.get("display_name")
        # 若 display_name 为空，则不校验
        if not display_name:
            return attrs
        application_id = self.context.get("application_id")
        source_type = attrs["source_type"]
        controller = init_volume_source_controller(source_type)
        if controller.list_by_app(application_id).filter(display_name=display_name).exists():
            raise serializers.ValidationError(_("已存在同名挂载资源"))
        return attrs


class DeleteMountSourcesSLZ(serializers.Serializer):
    # TODO: 更改为 resource_name 更合适
    source_name = serializers.CharField(help_text=_("挂载资源的名称"), required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)


class UpdateMountSourceSLZ(serializers.Serializer):
    # TODO: 更改为 resource_name 更合适
    source_name = serializers.CharField(help_text=_("挂载资源的名称"), required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)
    display_name = serializers.CharField(max_length=63, required=True)

    def validate(self, attrs):
        # 检查挂载资源 display_name 是否存在
        display_name = attrs.get("display_name")
        # 若 display_name 为空，则不校验
        if not display_name:
            return attrs
        application_id = self.context.get("application_id")
        source_type = attrs["source_type"]
        controller = init_volume_source_controller(source_type)
        # 更新时通过 name 索引， 排除掉自身
        query_set = controller.list_by_app(application_id).exclude(name=attrs["source_name"])
        if query_set.filter(display_name=display_name).exists():
            raise serializers.ValidationError(_("已存在同名挂载资源"))
        return attrs


class MountSourceSLZ(serializers.Serializer):
    application_id = serializers.UUIDField(required=True)
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=False)
    name = serializers.CharField(max_length=63, required=True)
    source_type = serializers.SerializerMethodField(label=_("挂载卷资源类型"))
    bound_modules = serializers.SerializerMethodField(label=_("已绑定模块信息"))
    data = serializers.JSONField(required=False)
    storage_size = serializers.CharField(required=False)
    storage_class_name = serializers.CharField(required=False)
    display_name = serializers.SerializerMethodField(label=_("显示名称"))

    def get_source_type(self, obj):
        if isinstance(obj, ConfigMapSource):
            return VolumeSourceType.ConfigMap.value
        elif isinstance(obj, PersistentStorageSource):
            return VolumeSourceType.PersistentStorage.value
        return None

    def get_bound_modules(self, obj):
        """返回已绑定的模块"""
        source_type = self.get_source_type(obj)
        controller = init_volume_source_controller(source_type)
        mounts = Mount.objects.filter(
            source_config=controller.build_volume_source(obj.name),
        )
        return [{"module": mount.module.name, "path": mount.mount_path} for mount in mounts]

    def get_display_name(self, obj):
        return obj.get_display_name()
