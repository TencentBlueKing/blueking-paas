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

from rest_framework import serializers

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.template_sync.status import get_sync_status, is_current
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate


class BuiltinTemplateOutputSLZ(serializers.Serializer):
    template_id = serializers.CharField(help_text="模板标识，即 SDK 创建沙箱时传入的 templateID，也是集群内的资源名")
    name = serializers.CharField(help_text="展示名称")
    description = serializers.CharField(help_text="描述")
    image = serializers.CharField(help_text="镜像")
    cpu_count = serializers.IntegerField(help_text="CPU 核数")
    memory_mb = serializers.IntegerField(help_text="内存（MB）")
    disk_size_mb = serializers.IntegerField(allow_null=True, help_text="系统盘（MB），为空表示未挂载独立系统盘")
    env_vars = serializers.DictField(child=serializers.CharField(), help_text="环境变量")
    workdir = serializers.CharField(help_text="工作目录")
    prewarm_count = serializers.IntegerField(help_text="每个集群预热的实例数")
    enabled = serializers.BooleanField(help_text="是否启用")
    is_public = serializers.BooleanField(help_text="是否在开发者中心展示")
    created = serializers.DateTimeField(help_text="创建时间")
    updated = serializers.DateTimeField(help_text="更新时间")


class TemplateSyncInputSLZ(serializers.Serializer):
    cluster_names = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
        help_text="只下发到这些集群，须已启用 e2b。不传表示全部启用 e2b 的集群",
    )
    resource_names = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
        help_text="只下发这些模板，按资源名指定。不传表示全部模板，限定模板时不清理其他模板的残留 CR",
    )

    def validate_cluster_names(self, cluster_names: list[str]) -> list[str]:
        enabled = set(ClusterE2BConfig.objects.filter(enabled=True).values_list("cluster__name", flat=True))
        if unknown := sorted(set(cluster_names) - enabled):
            raise serializers.ValidationError(f"集群未启用 e2b：{', '.join(unknown)}")
        return cluster_names

    def validate_resource_names(self, resource_names: list[str]) -> list[str]:
        existing = set(
            E2BSandboxTemplate.objects.filter(resource_name__in=resource_names).values_list("resource_name", flat=True)
        )
        if unknown := sorted(set(resource_names) - existing):
            raise serializers.ValidationError(f"模板不存在：{', '.join(unknown)}")
        return resource_names


class TemplateSyncOverviewQuerySLZ(serializers.Serializer):
    is_builtin = serializers.BooleanField(
        required=False, allow_null=True, default=None, help_text="只看内置或自定义模板"
    )
    status = serializers.ChoiceField(
        choices=E2BTemplateSyncStatus.get_choices(), required=False, help_text="按汇总状态过滤"
    )


class TemplateSyncStateOutputSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text="集群名称")
    status = serializers.SerializerMethodField(
        help_text="下发状态，pending / succeeded / failed。下发成功后模板又改了规格的按 pending 算"
    )
    message = serializers.CharField(help_text="失败原因")
    updated = serializers.DateTimeField(help_text="状态更新时间")
    up_to_date = serializers.SerializerMethodField(
        help_text="集群里是否已是模板的当前配置。为否时首选该集群的应用不能用这个模板创建沙箱"
    )

    def get_status(self, obj) -> str:
        return get_sync_status(obj, obj.template).value

    def get_up_to_date(self, obj) -> bool:
        return is_current(obj, obj.template)


class TemplateSyncOverviewOutputSLZ(serializers.Serializer):
    template_id = serializers.CharField(source="template.template_id", help_text="模板标识")
    is_builtin = serializers.BooleanField(source="template.is_builtin", help_text="是否内置模板")
    app_code = serializers.SerializerMethodField(help_text="自定义模板所属应用，内置模板为空")
    resource_name = serializers.CharField(source="template.resource_name", help_text="集群内的资源名")
    enabled = serializers.BooleanField(source="template.enabled", help_text="是否启用")
    status = serializers.CharField(
        allow_null=True,
        help_text="汇总状态：任一集群失败为 failed，否则任一集群未完成为 pending，全部成功为 succeeded；"
        "没有可下发的集群时为空",
    )
    states = TemplateSyncStateOutputSLZ(many=True, help_text="各目标集群的下发状态")
    missing = serializers.ListField(
        child=serializers.CharField(), help_text="是目标集群却没有下发状态的，需调用同步接口补齐"
    )

    def get_app_code(self, obj) -> str | None:
        app = obj.template.application
        return app.code if app else None


class ClusterSyncOverviewOutputSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text="集群名称")
    namespace = serializers.CharField(help_text="模板下发的命名空间")
    completed = serializers.BooleanField(help_text="应当下发到该集群的模板是否全部同步成功")
    succeeded = serializers.ListField(child=serializers.CharField(), help_text="同步成功的资源名")
    pending = serializers.ListField(child=serializers.CharField(), help_text="待同步的资源名")
    failed = serializers.DictField(child=serializers.CharField(), help_text="同步失败的资源名及原因")
    missing = serializers.ListField(
        child=serializers.CharField(), help_text="应当下发却没有下发状态的资源名，需调用同步接口补齐"
    )
