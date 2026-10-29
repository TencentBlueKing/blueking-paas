# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
import os
import re

import humanize
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, PersistentStorageSize, VolumeSourceType
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError
from paas_wl.bk_app.cnative.specs.mounts import init_volume_source_controller
from paas_wl.utils.error_codes import error_codes

from .models import AppModelRevision, ConfigMapSource, Mount, PersistentStorageSource

logger = logging.getLogger(__name__)

# Storage size utilities
_STORAGE_SIZE_PATTERN = re.compile(r"^(\d+)Gi$")


class AppModelRevisionSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelRevision object"""

    class Meta:
        model = AppModelRevision
        exclude = ("module_id", "yaml_value")


class ConfigMapSLZ(serializers.Serializer):
    """挂载卷内容 (configmap source) 序列化器

    文件由前端选择并在本地解析, 之后以 {文件名: 文本内容} 整体提交;
    后端在此确认链路上做服务端兜底校验: 文件后缀白名单, 单文件大小, 内容总大小.
    """

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

        allowed_extensions = {ext.lower().lstrip(".") for ext in settings.MOUNT_FILE_UPLOAD_ALLOWED_EXTENSIONS}
        total_size = 0
        for filename, content in data.items():
            if not filename:
                raise serializers.ValidationError("key cannot be empty")

            self._validate_file_extension(filename, allowed_extensions)
            content_size = len(content.encode("utf-8"))
            self._validate_file_size(filename, content_size)
            total_size += len(filename.encode("utf-8")) + content_size

        max_source_size = settings.MOUNT_FILE_UPLOAD_MAX_SOURCE_SIZE
        if total_size > max_source_size:
            raise error_codes.VOLUME_SOURCE_SIZE_EXCEEDED.f(
                _("挂载资源的内容总大小不能超过 {size_limit} 上限 (当前 {current_size})").format(
                    size_limit=humanize.naturalsize(max_source_size, binary=True),
                    current_size=humanize.naturalsize(total_size, binary=True),
                )
            )
        return data

    def _validate_file_extension(self, filename: str, allowed_extensions: set[str]) -> None:
        """校验文件后缀是否在上传白名单中

        白名单通过环境配置 MOUNT_FILE_UPLOAD_ALLOWED_EXTENSIONS 决定, 为空表示允许所有后缀.
        匹配规则: 取文件名的后缀部分 (os.path.splitext), 大小写不敏感, 白名单项可带前导点.

        :param filename: 文件名
        :param allowed_extensions: 规范化后的后缀白名单
        :raises error_codes.VOLUME_FILE_EXTENSION_NOT_ALLOWED: 当文件后缀不在白名单中时
        """
        if not allowed_extensions:
            return

        extension = os.path.splitext(filename)[1].lstrip(".").lower()
        if extension not in allowed_extensions:
            raise error_codes.VOLUME_FILE_EXTENSION_NOT_ALLOWED.f(
                _("仅允许上传以下后缀的文件: {extensions}").format(extensions=", ".join(sorted(allowed_extensions)))
            )

    def _validate_file_size(self, filename: str, content_size: int) -> None:
        """校验单个文件内容的大小, 上限由 MOUNT_FILE_UPLOAD_MAX_SIZE 配置

        :param filename: 文件名
        :param content_size: 文件内容的字节数
        :raises error_codes.VOLUME_FILE_TOO_LARGE: 当文件内容超过上限时
        """
        max_size = settings.MOUNT_FILE_UPLOAD_MAX_SIZE
        if content_size > max_size:
            raise error_codes.VOLUME_FILE_TOO_LARGE.f(
                _("文件 {filename} 的大小不能超过 {size_limit}").format(
                    filename=filename, size_limit=humanize.naturalsize(max_size, binary=True)
                )
            )


class PersistentStorageSLZ(serializers.Serializer):
    storage_size = serializers.CharField(help_text=_("持久存储容量，如 1Gi, 2Gi, 4Gi 或自定义值"), allow_null=True)

    def validate_storage_size(self, value: str) -> str:
        """验证存储大小"""

        if value is None:
            return value

        # 检查是否为预设容量
        preset_values = PersistentStorageSize.get_values()
        if value in preset_values:
            return value

        # 如果不是预设容量，检查是否允许自定义
        if not getattr(settings, "PERSISTENT_STORAGE_SIZE_ALLOW_CUSTOM", False):
            raise serializers.ValidationError(_("容量必须是以下选项之一: {}").format(", ".join(preset_values)))

        # 验证自定义容量
        try:
            size_value = self._parse_storage_size(value)
        except ValueError:
            raise serializers.ValidationError(_("自定义容量格式无效, 应为如 '5Gi' 的格式"))

        max_size = settings.PERSISTENT_STORAGE_SIZE_MAX

        # Note: 当前只支持 GB 单位, size 大小不可小于 1 GB
        if size_value < 1 or size_value > max_size:
            raise serializers.ValidationError(_("自定义容量必须在 1Gi 到 {}Gi 之间").format(max_size))

        return value

    def _parse_storage_size(self, size: str) -> int:
        """Parse storage size string, return value in Gi

        :param size: Storage size string, format: '<number>Gi', e.g. '5Gi'
        :returns: Parsed value in Gi
        :raises ValueError: When format is invalid
        """
        match = _STORAGE_SIZE_PATTERN.match(size)
        if match:
            return int(match.group(1))
        raise ValueError(f"Invalid storage size format: {size}")


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
    sub_paths = serializers.ListField(required=False, child=serializers.CharField(), help_text="子路径配置")

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
            "sub_paths",
        )

    def get_configmap_source(self, obj):
        if obj.source_type != VolumeSourceType.ConfigMap.value:
            return None
        try:
            controller = init_volume_source_controller(obj.source_type)
            source = controller.get_by_env(
                app_id=obj.module.application.id,
                env_name=obj.environment_name,
                source_name=obj.source_name,
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
                source_name=obj.source_name,
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
            raise serializers.ValidationError(_("预发布环境仅支持 1G 的持久存储"))

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
