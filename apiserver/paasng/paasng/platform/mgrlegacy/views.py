# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import datetime
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accounts.permissions.application import application_perm_required
from paasng.platform.applications.models import Application
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.mgrlegacy.constants import MigrationStatus

try:
    from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy
except ImportError:
    from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore

from paasng.platform.mgrlegacy.models import MigrationProcess
from paasng.platform.mgrlegacy.serializers import (
    ApplicationMigrationInfoSLZ,
    LegacyAppSLZ,
    LegacyAppStateSLZ,
    MigrationProcessConfirmSLZ,
    MigrationProcessCreateSLZ,
    MigrationProcessDetailSLZ,
    MigrationProcessOperateSLZ,
    QueryMigrationAppSLZ,
)
from paasng.platform.mgrlegacy.tasks import (
    confirm_with_rollback_on_failure,
    migrate_with_rollback_on_failure,
    rollback_migration_process,
)
from paasng.platform.mgrlegacy.utils import LegacyAppManager, check_operation_perms
from paasng.publish.entrance.exposer import get_exposed_url
from paasng.publish.sync_market.managers import AppDeveloperManger, AppManger
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class LegacyAppViewset(viewsets.ViewSet):
    """View class for applications"""

    def list(self, request):
        with console_db.session_scope() as session:
            serializer = QueryMigrationAppSLZ(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            params = serializer.data

            applications = AppDeveloperManger(session).get_apps_by_developer(username=request.user.username)
            legacy_apps = [LegacyAppManager(legacy_app, session) for legacy_app in applications]

            if params['result_type'] in ['todoMigrate', 'doneMigrate', 'cannotMigrate']:
                result_list = list(filter(lambda app: app.category == params['result_type'], legacy_apps))
            else:
                result_list = legacy_apps

            result_list.sort(key=lambda item: item.legacy_app.created_date or datetime.datetime.now(), reverse=True)

            serializer_data = [legacy_app.serialize_data() for legacy_app in result_list]
            serializer = LegacyAppSLZ(serializer_data, many=True)
            return Response({'count': len(result_list), 'data': serializer.data})

    @application_perm_required('view_application')
    def exposed_url_info(self, request, code, module_name=None):
        """根据 app code 查询应用的访问地址"""
        application = Application.objects.get(code=code)
        module = application.get_module(module_name)

        return Response(
            {
                "exposed_link": {
                    env.environment: getattr(get_exposed_url(env), 'address', None) for env in module.envs.all()
                }
            }
        )


class MigrationCreateViewset(viewsets.ModelViewSet):
    """View class for legacy app migration"""

    serializer_class = MigrationProcessCreateSLZ

    def create(self, request, *args, **kwargs):
        with console_db.session_scope() as session:
            context = self.get_serializer_context()
            serializer = self.serializer_class(context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            data['owner'] = data['owner'].pk
            data['session'] = session
            check_operation_perms(username=request.user.username, legacy_app_id=data['legacy_app_id'], session=session)
            migration_process, _ = MigrationProcess.objects.get_or_create_migration_process_for_legacy(**data)
            migrate_with_rollback_on_failure.apply_async(args=(migration_process.id,))
            response_serializer = MigrationProcessDetailSLZ(migration_process)
            return Response(data=response_serializer.data)


class MigrationDetailViewset(viewsets.ModelViewSet):
    serializer_class = MigrationProcessOperateSLZ

    def get_queryset(self):
        return MigrationProcess.objects.all().order_by('-id')

    def list(self, request, *args, **kwargs):
        migration_processes = self.get_queryset()
        response_serializer = MigrationProcessDetailSLZ(migration_processes, many=True)
        return Response(data=response_serializer.data)

    def state(self, request, id):
        migration_process = MigrationProcess.objects.get(id=id)
        with console_db.session_scope() as session:
            check_operation_perms(
                username=request.user.username, legacy_app_id=migration_process.legacy_app_id, session=session
            )

            response_serializer = MigrationProcessDetailSLZ(migration_process)
            return Response(data=response_serializer.data)

    def old_state(self, request, id):
        """应用在旧版开发者中心的状态"""
        migration_process = MigrationProcess.objects.get(id=id)
        with console_db.session_scope() as session:
            check_operation_perms(
                username=request.user.username, legacy_app_id=migration_process.legacy_app_id, session=session
            )
            legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
            legacy_app_proxy = LegacyAppProxy(legacy_app=legacy_app, session=session)
        response_data = {
            'is_prod_deployed': legacy_app_proxy.is_prod_deployed(),
            'is_stag_deployed': legacy_app_proxy.is_stag_deployed(),
            # 应用下架链接，应用未下架时需要指引用户去下架
            'offline_url': legacy_app_proxy.offline_url(),
            # 是否为第三方应用
            'is_third_app': legacy_app_proxy.is_third_app(),
        }
        response_serializer = LegacyAppStateSLZ(response_data)
        return Response(data=response_serializer.data)

    def rollback(self, request, id):
        """手动点击回滚"""
        force = request.data.get('force')
        with console_db.session_scope() as session:
            migration_process = MigrationProcess.objects.get(id=id)
            check_operation_perms(
                username=request.user.username, legacy_app_id=migration_process.legacy_app_id, session=session
            )

            # 只要确认迁移完成的应用就不允许回滚
            if not force:
                if migration_process.status == MigrationStatus.CONFIRMED.value:
                    return JsonResponse(data={'message': _('已确认后的应用无法回滚'), 'result': False}, status=403)

            # 应用必须在 PaaS3.0 全部下架后，才能回滚。否则会出现在 PaaS3.0 页面上看不到应用，但是应用进程还在的情况
            if migration_process.is_v3_prod_available() or migration_process.is_v3_stag_available():
                raise error_codes.APP_NOT_OFFLINE_IN_PAAS3

            rollback_migration_process.apply_async(args=(migration_process.id,))
            response_serializer = MigrationProcessDetailSLZ(migration_process)
            return Response(data=response_serializer.data)


class MigrationConfirmViewset(viewsets.GenericViewSet):
    lookup_field = "id"
    serializer_class = MigrationProcessConfirmSLZ

    def get_queryset(self):
        return MigrationProcess.objects.all().order_by('-id')

    def confirm(self, request, id):
        migration_process: MigrationProcess = self.get_object()
        # 检查用户是否有操作该应用迁移的权限
        with console_db.session_scope() as session:
            check_operation_perms(
                username=request.user.username, legacy_app_id=migration_process.legacy_app_id, session=session
            )
            legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
            legacy_app_proxy = LegacyAppProxy(legacy_app=legacy_app, session=session)

        # 仅当应用使用了引擎才检查部署相关内容，非引擎应用（带三方应用）不需要检查
        if migration_process.app.engine_enabled:
            # 检查该应用是否部署过
            if not (migration_process.is_v3_prod_available() or migration_process.is_v3_stag_available()):
                raise error_codes.APP_NOT_DEPLOYED_IN_ANY_ENV

            # 应用在 PaaS 2.0 上的测试环境&生产环境都已经下架，才可以确认迁移
            if legacy_app_proxy.is_stag_deployed() or legacy_app_proxy.is_prod_deployed():
                raise error_codes.APP_NOT_OFFLINE_IN_PAAS2

        # 调用 entrancemigration.migrate() => migration_process.append_migration()
        confirm_with_rollback_on_failure.apply_async(args=(migration_process.id,))
        return Response(data={"message": "success"}, status=status.HTTP_201_CREATED)


class ApplicationMigrationInfoAPIView(viewsets.ViewSet):
    def retrieve(self, request, code):
        migration_process_qs = MigrationProcess.objects.filter(app__code=code)
        has_migration_record = migration_process_qs.exists()
        is_need_alert_migration_timeout = False
        if has_migration_record:
            migration_process = migration_process_qs.latest('id')
            if migration_process.is_active():
                is_migration_timeout = (django_timezone.now() - migration_process.created) > datetime.timedelta(
                    days=settings.MIGRATION_REMIND_DAYS
                )
                is_need_alert_migration_timeout = is_migration_timeout

        data = {'is_need_alert_migration_timeout': is_need_alert_migration_timeout}
        slz = ApplicationMigrationInfoSLZ(instance=data)
        return Response(data=slz.data)
