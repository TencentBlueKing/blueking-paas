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

from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus


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


class TemplateSyncResultOutputSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text="集群名称")
    synced = serializers.ListField(child=serializers.CharField(), help_text="下发成功的资源名")
    failed = serializers.DictField(child=serializers.CharField(), help_text="下发失败的资源名及原因")
    pruned = serializers.ListField(child=serializers.CharField(), help_text="因模板已删除而被清理的资源名")
    error = serializers.CharField(help_text="集群级别的失败原因，如连不上集群，为空表示没有")


class TemplateSyncOverviewQuerySLZ(serializers.Serializer):
    is_builtin = serializers.BooleanField(
        required=False, allow_null=True, default=None, help_text="只看内置或自定义模板"
    )
    status = serializers.ChoiceField(
        choices=E2BTemplateSyncStatus.get_choices(), required=False, help_text="按汇总状态过滤"
    )


class TemplateSyncRecordOutputSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text="集群名称")
    status = serializers.CharField(help_text="下发状态，pending / succeeded / failed")
    message = serializers.CharField(help_text="失败原因")
    updated = serializers.DateTimeField(help_text="状态更新时间")


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
    records = TemplateSyncRecordOutputSLZ(many=True, help_text="各目标集群的下发状态")
    missing = serializers.ListField(
        child=serializers.CharField(), help_text="是目标集群却没有下发记录的，需调用同步接口补齐"
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
        child=serializers.CharField(), help_text="应当下发却没有记录的资源名，需调用同步接口补齐"
    )
