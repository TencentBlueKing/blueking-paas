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


from typing import List, Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.shim import ClusterAllocator, EnvClusterService
from paasng.accessories.publish.entrance.exposer import env_is_deployed, get_exposed_url
from paasng.core.region.models import get_region
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import get_tenant
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.serializers.app import UpdateApplicationNameSLZ
from paasng.platform.engine.constants import JobStatus, OperationTypes
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.utils.models import OrderByField
from paasng.utils.serializers import HumanizeDateTimeField, StringArrayField, UserNameField

# 应用列表序列化器


class ApplicationListOutputSLZ(serializers.Serializer):
    """应用序列化器"""

    logo = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用 logo")
    code = serializers.CharField(read_only=True, help_text="应用的唯一标识")
    name = serializers.CharField(read_only=True, help_text="应用名称")
    app_tenant_id = serializers.CharField(read_only=True, help_text="应用租户 ID")
    app_tenant_mode = serializers.CharField(read_only=True, help_text="应用租户模式")
    type = serializers.SerializerMethodField(read_only=True)
    resource_quotas = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.BooleanField(read_only=True, help_text="应用是否处于激活状态")
    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")
    tenant_id = serializers.CharField(read_only=True, help_text="应用所属租户 ID")

    def get_type(self, instance: Application) -> str:
        return ApplicationType.get_choice_label(instance.type)

    def get_resource_quotas(self, instance: Application) -> dict:
        """从 context 中获取应用的资源配额"""
        default_quotas = {"memory": "--", "cpu": "--"}
        app_resource_quotas = self.context.get("app_resource_quotas")

        if not app_resource_quotas:
            return default_quotas

        return app_resource_quotas.get(instance.code, default_quotas)


class ApplicationListFilterInputSLZ(serializers.Serializer):
    """应用列表过滤器序列化器"""

    valid_order_by_fields = {"is_active", "created", "updated"}

    search = serializers.CharField(required=False, help_text="应用名称/ID 关键字搜索")
    name = serializers.CharField(required=False, help_text="应用名称")
    tenant_id = serializers.CharField(required=False, help_text="应用所属租户")
    app_tenant_mode = serializers.ChoiceField(
        required=False,
        choices=AppTenantMode.get_choices(),
        help_text="应用租户模式",
    )
    type = serializers.ChoiceField(
        required=False,
        choices=ApplicationType.get_choices(),
        help_text="应用类型",
    )
    is_active = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="应用状态: true(正常) / false(下架), null 或不传表示不进行过滤",
    )
    order_by = StringArrayField(required=False, help_text="排序字段")

    def validate_order_by(self, fields: List[str]) -> List[str]:
        """校验排序字段"""
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise ValidationError(f"Invalid order_by field: {field}")

        return fields


class TenantAppStatisticsOutputSLZ(serializers.Serializer):
    """租户应用统计序列化器"""

    tenant_id = serializers.CharField(help_text="租户 ID")
    app_count = serializers.IntegerField(help_text="应用数量")


class TenantModeListOutputSLZ(serializers.Serializer):
    """租户模式序列化器"""

    type = serializers.CharField(help_text="租户模式")
    label = serializers.CharField(help_text="租户模式标签")


class ApplicationTypeOutputSLZ(serializers.Serializer):
    """应用类型序列化器"""

    type = serializers.CharField(help_text="应用类型")
    label = serializers.CharField(help_text="应用类型标签")


# 应用详情序列化器


class ApplicationBasicInfoSLZ(serializers.Serializer):
    """应用基本信息序列化器"""

    code = serializers.CharField(read_only=True, help_text="应用 ID")
    name = serializers.CharField(read_only=True, help_text="应用名称")
    app_tenant_mode = serializers.CharField(read_only=True, help_text="应用租户模式")
    app_tenant_id = serializers.CharField(read_only=True, help_text="应用租户 ID")
    type = serializers.CharField(read_only=True, help_text="应用类型")
    is_active = serializers.BooleanField(read_only=True, help_text="应用状态")
    creator = UserNameField(read_only=True, help_text="创建人")
    created_humanized = HumanizeDateTimeField(source="created", help_text="创建时间")
    tenant_id = serializers.CharField(read_only=True, help_text="应用所属租户 ID")


class ApplicationEnvironmentOperationSLZ(serializers.Serializer):
    """应用环境操作序列化器"""

    operator = UserNameField(read_only=True, help_text="操作人")
    updated = serializers.DateTimeField(read_only=True, help_text="操作时间")
    operation_type = serializers.CharField(read_only=True, help_text="操作类型")
    status = serializers.CharField(read_only=True, help_text="操作状态")


class ApplicationEnvironmentSLZ(serializers.Serializer):
    """应用环境序列化器"""

    name = serializers.CharField(source="environment", read_only=True, help_text="环境名称")
    is_deployed = serializers.SerializerMethodField(help_text="是否已部署", read_only=True)
    exposed_url = serializers.SerializerMethodField(help_text="访问链接, 未部署时为 None", read_only=True)
    deploy_cluster = serializers.SerializerMethodField(help_text="部署集群")
    recent_operation = serializers.SerializerMethodField(help_text="最近操作")

    def get_is_deployed(self, env) -> bool:
        """获取环境是否已部署"""
        return env_is_deployed(env)

    def get_exposed_url(self, env) -> Optional[str]:
        exposed_link = get_exposed_url(env)
        return exposed_link.address if exposed_link else None

    def get_deploy_cluster(self, env) -> str:
        """获取集群名称"""
        try:
            cluster = EnvClusterService(env).get_cluster()
        except Cluster.DoesNotExist:
            return ""
        else:
            return cluster.name

    def get_recent_operation(self, env) -> Optional[dict]:
        """获取最近操作"""
        last_op = ModuleEnvironmentOperations.objects.filter(app_environment=env).order_by("-created").first()
        if not last_op:
            return None
        operator = last_op.operator.username
        updated = last_op.created.strftime("%Y-%m-%d %H:%M:%S")
        operation_type = OperationTypes.get_choice_label(last_op.operation_type)
        status = JobStatus.get_choice_label(last_op.status)
        message = _("于{time}{operation}{status}").format(time=updated, operation=operation_type, status=status)

        return {"operator": operator, "message": message}


class ApplicationModuleSLZ(serializers.Serializer):
    """应用模块序列化器"""

    name = serializers.CharField(read_only=True, help_text="模块名称")
    is_default = serializers.BooleanField(read_only=True, help_text="是否默认模块")
    environment = ApplicationEnvironmentSLZ(source="envs.all", many=True, read_only=True, help_text="环境信息")


class ApplicationAdminInfoSLZ(serializers.Serializer):
    """应用管理员信息序列化器"""

    user_is_admin_in_app = serializers.BooleanField(help_text="当前用户是否为应用管理员")
    show_plugin_admin_operations = serializers.BooleanField(help_text="是否显示插件管理员相关操作")
    user_is_admin_in_plugin = serializers.BooleanField(help_text="是否为插件管理员", allow_null=True)


class ApplicationDetailOutputSLZ(serializers.Serializer):
    """应用详情序列化器"""

    basic_info = ApplicationBasicInfoSLZ(read_only=True, help_text="应用基本信息")
    app_admin = ApplicationAdminInfoSLZ(read_only=True, help_text="应用管理员信息")
    modules_info = serializers.ListField(child=ApplicationModuleSLZ(), help_text="应用模块信息", read_only=True)


class ApplicationNameUpdateInputSLZ(UpdateApplicationNameSLZ):
    """更新应用名称序列化器"""


class UpdateApplicationBindClusterSLZ(serializers.Serializer):
    """更新应用集群序列化器"""

    name = serializers.CharField(required=True, help_text="集群名称")

    def validate_name(self, name: str) -> str:
        """验证集群名称"""
        cur_user = self.context["user"]
        environment = self.context["environment"]
        region = self.context["region"]

        ctx = AllocationContext(
            tenant_id=get_tenant(cur_user).id,
            region=get_region(region),
            environment=environment,
            username=cur_user.username,
        )
        if not ClusterAllocator(ctx).check_available(name):
            raise ValidationError(_("现有的分配策略下未找到匹配的集群(集群名: {name})").format(name=name))

        return name


class DeletedApplicationListOutputSLZ(serializers.Serializer):
    """软删除应用序列化器"""

    logo = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用 logo")
    code = serializers.CharField(read_only=True, help_text="应用的唯一标识")
    name = serializers.CharField(read_only=True, help_text="应用名称")
    app_tenant_id = serializers.CharField(read_only=True, help_text="应用租户 ID")
    app_tenant_mode = serializers.CharField(read_only=True, help_text="应用租户模式")
    type = serializers.SerializerMethodField(read_only=True)
    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")
    tenant_id = serializers.CharField(read_only=True, help_text="应用所属租户 ID")
    deleted_time = HumanizeDateTimeField(source="updated")

    def get_type(self, instance: Application) -> str:
        return ApplicationType.get_choice_label(instance.type)
