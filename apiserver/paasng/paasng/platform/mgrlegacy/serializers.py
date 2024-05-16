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
from typing import Dict, List

from rest_framework import serializers

from paas_wl.bk_app.processes.serializers import InstanceListSLZ, ProcessListSLZ
from paasng.platform.mgrlegacy.constants import CNativeMigrationStatus
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess, MigrationProcess
from paasng.utils.i18n.serializers import DjangoTranslatedCharField


class MigrationRunResult(serializers.Serializer):
    """migration 步骤执行结果"""

    name = serializers.CharField(help_text="步骤名称")
    description = DjangoTranslatedCharField(help_text="步骤描述")
    failed_reason = DjangoTranslatedCharField(help_text="失败原因")
    log = serializers.CharField(help_text="日志")
    successful = serializers.BooleanField(help_text="是否成功")
    apply_type = serializers.CharField(help_text="类型")
    finished = serializers.BooleanField(help_text="是否完成")
    msecs_cost = serializers.FloatField(help_text="执行时长")
    created_ts = serializers.FloatField(default=0)


class LegacyAppSLZ(serializers.Serializer):
    category = serializers.CharField(help_text="迁移分类")
    legacy_app_id = serializers.IntegerField(help_text="应用ID")
    code = serializers.CharField(help_text="应用编码")
    name = serializers.CharField(help_text="应用名称")
    logo = serializers.CharField(help_text="LOGO地址")
    tag = serializers.CharField(help_text="标签")
    not_support_reasons = serializers.ListField(help_text="暂不支持迁移的原因")
    language = serializers.CharField(help_text="开发语言")
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", help_text="创建时间")
    latest_migration_id = serializers.IntegerField(help_text="绑定的迁移记录ID")
    finished_migration = serializers.BooleanField(help_text="是否已经迁移完成")
    is_active = serializers.BooleanField(help_text="latest_migration_id是否是活动状态")
    is_prod_deployed = serializers.BooleanField(help_text="正式环境已上线，且没有下架")
    has_prod_deployed_before_migration = serializers.BooleanField(help_text="迁移前正式环境上线过")
    stag_exposed_link = serializers.CharField(help_text="app测试环境地址")
    prod_exposed_link = serializers.CharField(help_text="app正式环境地址")
    region = serializers.CharField(help_text="版本")
    migration_finished_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", help_text="迁移完成时间")
    legacy_url = serializers.CharField(help_text="PaaS2.0上的访问地址")

    class Meta:
        fields = (
            "legacy_app_id",
            "code",
            "name",
            "logo",
            "tag",
            "language",
            "is_prod_deployed",
            "has_prod_deployed_before_migration",
            "created",
            "migration_finished_date",
        )


class LegacyAppStateSLZ(serializers.Serializer):
    is_prod_deployed = serializers.BooleanField(help_text="PaaS2.0 上正式环境是否已下架")
    is_stag_deployed = serializers.BooleanField(help_text="PaaS2.0 上测试环境是否已下架")
    offline_url = serializers.CharField(help_text="PaaS2.0 上的下架链接")
    is_third_app = serializers.BooleanField(help_text="是否为第三方应用")


class MigrationProcessCreateSLZ(serializers.ModelSerializer):
    legacy_app_id = serializers.IntegerField(help_text="应用ID")
    owner = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = MigrationProcess
        fields = ("legacy_app_id", "owner")


class MigrationProcessDetailSLZ(serializers.ModelSerializer):
    ongoing_migration = MigrationRunResult()
    finished_migrations = MigrationRunResult(many=True)
    finished_rollbacks = MigrationRunResult(many=True)
    finished_operations = MigrationRunResult(many=True)
    is_active = serializers.BooleanField()
    is_v3_prod_available = serializers.BooleanField()
    is_v3_stag_available = serializers.BooleanField()

    class Meta:
        model = MigrationProcess
        fields = "__all__"


class MigrationProcessOperateSLZ(serializers.Serializer):
    pass


class MigrationProcessConfirmSLZ(serializers.Serializer):
    pass


class QueryMigrationAppSLZ(serializers.Serializer):
    result_type = serializers.ChoiceField(
        choices=(
            ("doneMigrate", "doneMigrate"),
            ("todoMigrate", "todoMigrate"),
            ("cannotMigrate", "cannotMigrate"),
            ("all", "all"),
        ),
        default="all",
    )


class ApplicationMigrationInfoSLZ(serializers.Serializer):
    is_need_alert_migration_timeout = serializers.BooleanField(help_text="是否需要提醒迁移超时了")


class CNativeMigrationProcessSLZ(serializers.ModelSerializer):
    error_msg = serializers.SerializerMethodField(help_text="错误信息")
    details = serializers.SerializerMethodField(help_text="详情")

    class Meta:
        model = CNativeMigrationProcess
        fields = ("id", "status", "error_msg", "details", "created_at", "confirm_at", "is_active")

    def get_error_msg(self, obj: CNativeMigrationProcess) -> str:
        if obj.status == CNativeMigrationStatus.MIGRATION_FAILED.value:
            # 仅有一个有效的错误信息
            return next((m.error_msg for m in obj.details.migrations if m.error_msg), "")
        elif obj.status == CNativeMigrationStatus.ROLLBACK_FAILED.value:
            # 仅有一个有效的错误信息
            return next((m.error_msg for m in obj.details.rollbacks if m.error_msg), "")
        return ""

    def get_details(self, obj: CNativeMigrationProcess) -> Dict[str, List]:
        return {
            "migrations": [
                {"migrator_name": m.migrator_name, "is_succeeded": m.is_succeeded, "error_msg": m.error_msg}
                for m in obj.details.migrations
            ]
        }


class ListProcessesSLZ(serializers.Serializer):
    processes = ProcessListSLZ()
    instances = InstanceListSLZ()
    process_packages = serializers.ListField(required=False, child=serializers.DictField())
