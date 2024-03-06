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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, PersistentStorageSize, VolumeSourceType
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError
from paas_wl.bk_app.cnative.specs.mounts import init_source_controller

from .constants import DeployStatus
from .models import AppModelDeploy, AppModelRevision, ConfigMapSource, Mount, PersistentStorageSource

logger = logging.getLogger(__name__)


class AppModelResourceSerializer(serializers.Serializer):
    """云原生架构应用 Serializer"""

    application_id = serializers.UUIDField(label=_("所属应用"))
    module_id = serializers.UUIDField(label=_("所属模块"))
    manifest = serializers.JSONField(label=_("BkApp 配置信息"), source="revision.json_value")


class CreateDeploySerializer(serializers.Serializer):
    """部署云原生应用 Serializer"""

    # TODO: 后续支持版本与部署分离，可以通过指定版本号的方式部署
    # 不提供时，使用应用当前 revision 所指向的 manifest 值
    manifest = serializers.JSONField(label=_("BkApp 配置信息"), required=False)


class ProcReplicasChangeSLZ(serializers.Serializer):
    """Format `ProcReplicasChange` object"""

    proc_type = serializers.CharField(label=_("进程类型"))
    old = serializers.IntegerField(label=_("旧副本数"))
    new = serializers.IntegerField(label=_("新副本数"))


class DeployPrepResultSLZ(serializers.Serializer):
    """Format deploy preparation result"""

    proc_replicas_changes = serializers.ListField(label=_("进程副本数变化"), child=ProcReplicasChangeSLZ())


class QueryDeploysSerializer(serializers.Serializer):
    """Serializer for querying AppModelDeploy objects"""

    operator = serializers.CharField(label=_("操作者"), required=False)


class DeployDetailSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelDeploy object"""

    manifest = serializers.JSONField(label=_("BkApp 配置信息"), source="revision.json_value")
    operator = serializers.CharField(source="operator.username")

    class Meta:
        model = AppModelDeploy
        exclude = ("module_id",)


class AppModelRevisionSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelDeploy object"""

    class Meta:
        model = AppModelRevision
        exclude = ("module_id", "yaml_value")


class DeploySerializer(serializers.ModelSerializer):
    """Serializer for representing AppModelDeploy objects"""

    operator = serializers.CharField(source="operator.username")

    class Meta:
        model = AppModelDeploy
        exclude = ("module_id",)


class MresDeploymentStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource deployment status"""

    deploy_id = serializers.IntegerField(help_text="部署ID", source="pk")
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)
    last_transition_time = serializers.DateTimeField()

    operator = serializers.CharField(source="operator.username", help_text="操作人")
    created = serializers.DateTimeField(help_text="发布时间")


class MresIngressInfoSLZ(serializers.Serializer):
    """Serializer for ModelResource Ingress info"""

    url = serializers.CharField(allow_null=True, allow_blank=True)


class MresConditionSLZ(serializers.Serializer):
    """Serializer for ModelResource Condition Field"""

    type = serializers.CharField()
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)


class KubeEventSLZ(serializers.Serializer):
    """Serializer for k8s event"""

    name = serializers.CharField(help_text="事件名称")
    type = serializers.CharField(help_text="事件级别")
    reason = serializers.CharField(help_text="事件原因")
    count = serializers.CharField(help_text="事件累计触发次数")
    message = serializers.CharField(help_text="事件消息内容")
    source_component = serializers.CharField(help_text="事件来源组件")
    first_seen = serializers.DateTimeField(help_text="事件首次被记录的时间")
    last_seen = serializers.DateTimeField(help_text="事件最后被记录的时间")


class MresStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource status"""

    deployment = MresDeploymentStatusSLZ()
    ingress = MresIngressInfoSLZ()
    conditions = MresConditionSLZ(many=True)
    events = KubeEventSLZ(many=True)


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

    def validate_source_config_data(self, value):
        if not value:
            return None
        for key in value:
            if not key:
                raise serializers.ValidationError("key cannot be empty")
        return value


class PersistentStorageSLZ(serializers.Serializer):
    storage = serializers.ChoiceField(choices=PersistentStorageSize.get_choices(), allow_null=True)


class UpsertMountSLZ(serializers.Serializer):
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=True)
    name = serializers.RegexField(
        help_text=_("挂载卷名称"), regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63, required=True
    )
    # 该正则匹配以'/'开头，不包含空字符(\0)和连续'/'的文件路径，且根目录'/'不合法
    # 合法路径：/xxx/ 和 /xxx  非法路径：/ 和 /xxx//
    mount_path = serializers.RegexField(regex=r"^/([^/\0]+(/)?)+$", required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)
    source_name = serializers.CharField(help_text="共享挂载资源的名称", allow_blank=True, required=False)
    configmap_source = ConfigMapSLZ(required=False, allow_null=True)
    persistent_storage_source = PersistentStorageSLZ(required=False, allow_null=True)

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
            "region",
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
            controller = init_source_controller(obj.source_type)
            source = controller.get_by_mount(obj)
        except ValueError as e:
            raise GetSourceConfigDataError(_("获取挂载卷内容信息失败")) from e
        else:
            return {"source_config_data": source.data}

    def get_persistent_storage_source(self, obj):
        if obj.source_type != VolumeSourceType.PersistentStorage.value:
            return None
        try:
            controller = init_source_controller(obj.source_type)
            source = controller.get_by_mount(obj)
        except ValueError as e:
            raise GetSourceConfigDataError(_("获取挂载卷内容信息失败")) from e
        else:
            return {"storage": source.storage}


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


class DeleteMountSourcesSLZ(serializers.Serializer):
    source_name = serializers.CharField(help_text=_("挂载资源的名称"), required=True)
    source_type = serializers.ChoiceField(choices=VolumeSourceType.get_choices(), required=True)


class MountSourceSLZ(serializers.Serializer):
    application_id = serializers.UUIDField(required=True)
    environment_name = serializers.ChoiceField(choices=MountEnvName.get_choices(), required=False)
    name = serializers.CharField(max_length=63, required=True)
    source_type = serializers.SerializerMethodField(label=_("挂载卷资源类型"))
    binded_modules = serializers.SerializerMethodField(label=_("已绑定模块信息"))
    data = serializers.JSONField(required=False)
    storage = serializers.CharField(required=False)
    storage_class_name = serializers.CharField(required=False)

    def get_source_type(self, obj):
        if isinstance(obj, ConfigMapSource):
            return VolumeSourceType.ConfigMap.value
        elif isinstance(obj, PersistentStorageSource):
            return VolumeSourceType.PersistentStorage.value
        return None

    def get_binded_modules(self, obj):
        """返回已绑定的模块"""
        source_type = self.get_source_type(obj)
        controller = init_source_controller(source_type)
        mounts = Mount.objects.filter(
            source_config=controller.new_volume_source(obj.name),
        )
        return [(mount.name, mount.mount_path) for mount in mounts]
