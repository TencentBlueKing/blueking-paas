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
from collections import defaultdict
from typing import List

from django.conf import settings
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _

from paasng.accessories.iam.exceptions import BKIAMGatewayServiceError
from paasng.accessories.iam.helpers import add_role_members, fetch_application_members, remove_user_all_roles
from paasng.engine.models import EngineApp
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.helpers import register_builtin_user_groups_and_grade_manager
from paasng.platform.applications.models import Application
from paasng.platform.applications.utils import create_default_module
from paasng.platform.mgrlegacy.constants import AppMember
from paasng.platform.mgrlegacy.models import MigrationProcess
from paasng.platform.modules.constants import APP_CATEGORY, ExposedURLType, SourceOrigin
from paasng.platform.modules.helpers import get_image_labels_by_module
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.oauth2.models import OAuth2Client
from paasng.publish.sync_market.handlers import application_oauth_handler
from paasng.utils.error_codes import error_codes

from .base import BaseMigration


class BaseObjectMigration(BaseMigration):
    """
    Migrate application object, must happen first
    - Create Application object in database
    """

    def get_description(self):
        return _("创建应用对象")

    def migrate(self):
        region = self.context.legacy_app_proxy.to_paasv3_region()
        creator = self.context.legacy_app_proxy.get_app_creator_id(self.context.owner)
        type_ = self._get_type(self.context.legacy_app_proxy.is_third_app())
        # 应用也需要添加是否为 smart 应用的标记，会对 smart 应用做一些特殊处理，比如不能新增模块
        is_smart_app = self.context.legacy_app_proxy.is_smart()

        # 兼容某些极端情况下，回滚的时候没有删除 app，再次迁移报错的情况
        app, _ = Application.objects.update_or_create(
            code=self.legacy_app.code,
            defaults={
                'owner': creator,
                'creator': creator,
                'region': region,
                'name': self.legacy_app.name,
                'name_en': self.legacy_app.name,
                'language': self.context.legacy_app_proxy.get_language(),
                'type': type_.value,
                'is_deleted': False,
                'is_smart_app': is_smart_app,
            },
        )
        app.created = self.legacy_app.created_date
        # 为什么不在这里绑定 migration_process 和 Application ?
        # app.migrationprocess_set.add(self.context.migration_process)
        app.save(update_fields=['created'])

        self.context.app = app

    def rollback(self):
        # rollback application
        if self.context.app is not None:
            MigrationProcess.objects.filter(app=self.context.app).update(app=None)
            self.context.app.operation_set.all().delete()
            Application.objects.filter(pk=self.context.app.pk).delete()
        self.context.app = None  # type: ignore

    @staticmethod
    def _get_type(is_third_app: bool) -> ApplicationType:
        """Get application type"""
        if is_third_app:
            return ApplicationType.ENGINELESS_APP
        return ApplicationType.DEFAULT


class MainInfoMigration(BaseMigration):
    """Migrate main information of application, must happen first to provide
    the newlly created application object.
    - Create SourceCtl object
    """

    def get_description(self):
        return _("同步应用基本信息")

    def add_application_role(self, app_members: List[AppMember]) -> bool:
        """sync application roles"""
        try:
            register_builtin_user_groups_and_grade_manager(self.context.app)
        except BKIAMGatewayServiceError as e:
            raise error_codes.INITIALIZE_APP_MEMBERS_ERROR.f(e.message)

        role_members = defaultdict(list)
        for m in app_members:
            role_members[m.role].append(m.username)

        for role, members in role_members.items():
            add_role_members(app_code=self.context.app.code, role=ApplicationRole(role), usernames=members)

        return True

    def add_engine_app(self):
        # Initialize paas3.0 engine app
        # 应用类型
        if self.context.legacy_app_proxy.is_smart():
            source_origin = SourceOrigin.S_MART
        else:
            source_origin = SourceOrigin.AUTHORIZED_VCS

        module = create_default_module(
            self.context.app,
            language=self.context.legacy_app_proxy.get_language(),
            source_init_template=self.context.legacy_app_proxy.get_source_init_template(),
            source_origin=source_origin,
        )

        if self.context.legacy_app_proxy.is_from_legacy_v1():
            # V1 PaaS应用不支持使用独立子域名方法进行访问(bk_sid的cookies域导致)
            module.exposed_url_type = ExposedURLType.SUBPATH.value
            module.save()

        initializer = ModuleInitializer(module)
        initializer.create_engine_apps()

        if self.context.legacy_app_proxy.is_smart():
            # smart 应用按 PaaS3.0 一样的规则根据label筛选应用
            runtime_labels = get_image_labels_by_module(module)
        else:
            # 普通应用，统一用 legacy 镜像
            runtime_labels = {"category": APP_CATEGORY.LEGACY_APP.value}
        # 绑定初始运行环境，老版本的镜像可能已经被隐藏，需要显示指定查询所有的镜像
        initializer.bind_runtime_by_labels(runtime_labels, contain_hidden=True)
        initializer.initialize_log_config()

    def migrate(self):
        # 第三方应用（非引擎应用）仅创建默认模块，不创建 engine 相关信息
        if self.context.legacy_app_proxy.is_third_app():
            create_default_module(self.context.app)
        else:
            self.add_engine_app()

        # 由 bk-oauth 服务纳管应用信息后，则不需要再往 OAuth2Client 表中同步数据
        if not settings.ENABLE_BK_OAUTH:
            # Disable signal to avoid data sync
            post_save.disconnect(receiver=application_oauth_handler, sender=OAuth2Client)
            OAuth2Client.objects.get_or_create(
                region=self.context.app.region,
                client_id=self.context.app.code,
                defaults={'client_secret': self.context.legacy_app_proxy.get_secret_key()},
            )
            post_save.connect(receiver=application_oauth_handler, sender=OAuth2Client)

        # 添加应用成员
        app_members = self.context.legacy_app_proxy.get_app_members(self.context.owner)
        self.add_application_role(app_members)

    def rollback(self):
        # rollback oauth2
        OAuth2Client.objects.filter(client_id=self.context.app.code).delete()

        # rollback application service attachment
        for env in self.context.app.envs.all():
            env.engine_app.service_attachment.all().delete()
        engine_app_ids = list(self.context.app.envs.values_list('engine_app__id', flat=True))
        engine_app_ids = [item.hex for item in engine_app_ids]
        self.context.app.envs.all().delete()
        self.context.app.modules.all().delete()
        if engine_app_ids:
            EngineApp.objects.filter(id__in=engine_app_ids).delete()

        # rollback developers and administrators
        usernames = [m['username'] for m in fetch_application_members(self.context.app.code)]
        remove_user_all_roles(self.context.app.code, usernames)
