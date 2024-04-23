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
import datetime
import logging

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.deploy.app_res.controllers import ProcessesHandler
from paas_wl.bk_app.mgrlegacy.processes import get_processes_info
from paas_wl.bk_app.processes.constants import ProcessUpdateType
from paas_wl.bk_app.processes.serializers import UpdateProcessSLZ
from paas_wl.infras.resources.generation.mapper import get_mapper_proc_config_latest
from paas_wl.workloads.networking.entrance.serializers import ModuleEntrancesSLZ
from paasng.core.core.storages.sqlalchemy import console_db
from paasng.infras.accounts.permissions.application import application_perm_class, check_application_perm
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.mgrlegacy.cnative_migrations.wl_app import WlAppBackupManager
from paasng.platform.mgrlegacy.constants import CNativeMigrationStatus, MigrationStatus

try:
    from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy
except ImportError:
    from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore

from paas_wl.utils.error_codes import error_codes as wl_error_codes
from paasng.accessories.publish.entrance.exposer import get_exposed_url
from paasng.accessories.publish.sync_market.managers import AppDeveloperManger, AppManger
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess, MigrationProcess
from paasng.platform.mgrlegacy.serializers import (
    ApplicationMigrationInfoSLZ,
    CNativeMigrationProcessSLZ,
    LegacyAppSLZ,
    LegacyAppStateSLZ,
    ListProcessesSLZ,
    MigrationProcessConfirmSLZ,
    MigrationProcessCreateSLZ,
    MigrationProcessDetailSLZ,
    MigrationProcessOperateSLZ,
    QueryMigrationAppSLZ,
)
from paasng.platform.mgrlegacy.tasks import (
    confirm_migration,
    confirm_with_rollback_on_failure,
    migrate_default_to_cnative,
    migrate_with_rollback_on_failure,
    rollback_cnative_to_default,
    rollback_migration_process,
)
from paasng.platform.mgrlegacy.utils import LegacyAppManager, check_operation_perms
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

            if params["result_type"] in ["todoMigrate", "doneMigrate", "cannotMigrate"]:
                result_list = list(filter(lambda app: app.category == params["result_type"], legacy_apps))
            else:
                result_list = legacy_apps

            result_list.sort(key=lambda item: item.legacy_app.created_date or datetime.datetime.now(), reverse=True)

            serializer_data = [legacy_app.serialize_data() for legacy_app in result_list]
            serializer = LegacyAppSLZ(serializer_data, many=True)
            return Response({"count": len(result_list), "data": serializer.data})

    def exposed_url_info(self, request, code, module_name=None):
        """根据 app code 查询应用的访问地址"""
        application = Application.objects.get(code=code)
        check_application_perm(request.user, application, AppAction.VIEW_BASIC_INFO)
        module = application.get_module(module_name)

        return Response(
            {
                "exposed_link": {
                    env.environment: getattr(get_exposed_url(env), "address", None) for env in module.envs.all()
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
            data["owner"] = data["owner"].pk
            data["session"] = session
            check_operation_perms(username=request.user.username, legacy_app_id=data["legacy_app_id"], session=session)
            migration_process, _ = MigrationProcess.objects.get_or_create_migration_process_for_legacy(**data)
            migrate_with_rollback_on_failure.apply_async(args=(migration_process.id,))
            response_serializer = MigrationProcessDetailSLZ(migration_process)
            return Response(data=response_serializer.data)


class MigrationDetailViewset(viewsets.ModelViewSet):
    serializer_class = MigrationProcessOperateSLZ

    def get_queryset(self):
        return MigrationProcess.objects.all().order_by("-id")

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
            "is_prod_deployed": legacy_app_proxy.is_prod_deployed(),
            "is_stag_deployed": legacy_app_proxy.is_stag_deployed(),
            # 应用下架链接，应用未下架时需要指引用户去下架
            "offline_url": legacy_app_proxy.offline_url(),
            # 是否为第三方应用
            "is_third_app": legacy_app_proxy.is_third_app(),
        }
        response_serializer = LegacyAppStateSLZ(response_data)
        return Response(data=response_serializer.data)

    def rollback(self, request, id):
        """手动点击回滚"""
        force = request.data.get("force")
        with console_db.session_scope() as session:
            migration_process = MigrationProcess.objects.get(id=id)
            check_operation_perms(
                username=request.user.username, legacy_app_id=migration_process.legacy_app_id, session=session
            )

            # 只要确认迁移完成的应用就不允许回滚
            if not force and migration_process.status == MigrationStatus.CONFIRMED.value:
                return JsonResponse(data={"message": _("已确认后的应用无法回滚"), "result": False}, status=403)

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
        return MigrationProcess.objects.all().order_by("-id")

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
            migration_process = migration_process_qs.latest("id")
            if migration_process.is_active():
                is_migration_timeout = (django_timezone.now() - migration_process.created) > datetime.timedelta(
                    days=settings.MIGRATION_REMIND_DAYS
                )
                is_need_alert_migration_timeout = is_migration_timeout

        data = {"is_need_alert_migration_timeout": is_need_alert_migration_timeout}
        slz = ApplicationMigrationInfoSLZ(instance=data)
        return Response(data=slz.data)


class CNativeMigrationViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """
    普通应用向云原生应用迁移的相关接口
    """

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def migrate(self, request, code):
        """迁移普通应用到云原生应用

        NOTE: 仅迁移应用在平台侧的配置数据
        """
        app = self.get_application()

        if app.type == ApplicationType.CLOUD_NATIVE.value:
            raise error_codes.APP_MIGRATION_FAILED.f("该应用已是云原生应用，无法迁移")

        if (last_process := CNativeMigrationProcess.objects.filter(app=app).last()) and last_process.is_active():
            raise error_codes.APP_MIGRATION_FAILED.f("该应用正在变更中, 无法迁移")

        migration_process = CNativeMigrationProcess.create_migration_process(app, request.user.pk)
        process_id = migration_process.id
        migrate_default_to_cnative.delay(process_id)

        return Response({"process_id": process_id}, status=status.HTTP_201_CREATED)

    def rollback(self, request, code):
        """回滚云原生应用到普通应用

        NOTE: 只有上一次迁移成功的应用才可能需要回滚
        """
        app = self.get_application()

        if app.type != ApplicationType.CLOUD_NATIVE.value:
            raise error_codes.APP_ROLLBACK_FAILED.f("该应用非云原生应用，无法回滚")

        # 根据最新的迁移记录, 判断是否可以回滚
        if last_process := CNativeMigrationProcess.objects.filter(app=app).last():
            if last_process.is_active():
                raise error_codes.APP_ROLLBACK_FAILED.f("该应用正在变更中, 无法回滚")
            if last_process.status != CNativeMigrationStatus.MIGRATION_SUCCEEDED.value:
                raise error_codes.APP_ROLLBACK_FAILED.f(f"该应用处于 {last_process.status} 状态, 无法回滚")
        else:
            raise error_codes.APP_ROLLBACK_FAILED.f("该应用未进行过迁移, 无法回滚")

        rollback_process = CNativeMigrationProcess.create_rollback_process(app, request.user.pk)
        process_id = rollback_process.id
        rollback_cnative_to_default.delay(process_id, last_process.id)

        return Response({"process_id": process_id}, status=status.HTTP_201_CREATED)

    def get_process_by_id(self, request, process_id):
        """根据迁移记录 id 获取迁移记录"""
        process = get_object_or_404(CNativeMigrationProcess, id=process_id)
        slz = CNativeMigrationProcessSLZ(process)
        return Response(data=slz.data)

    def get_latest_process(self, request, code):
        """获取最新的迁移记录"""
        app = self.get_application()

        try:
            process = CNativeMigrationProcess.objects.filter(app=app).latest()
        except CNativeMigrationProcess.DoesNotExist:
            raise Http404("no process found")
        else:
            slz = CNativeMigrationProcessSLZ(process)
            return Response(data=slz.data)

    def list_processes(self, request, code):
        """获取当前应用的所有迁移记录"""
        app = self.get_application()
        processes = CNativeMigrationProcess.objects.filter(app=app)
        slz = CNativeMigrationProcessSLZ(processes, many=True)
        return Response(data=slz.data)

    def confirm(self, request, process_id):
        """确认迁移"""
        process = get_object_or_404(CNativeMigrationProcess, id=process_id)

        if process.status != CNativeMigrationStatus.MIGRATION_SUCCEEDED.value:
            raise error_codes.APP_MIGRATION_CONFIRMED_FAILED.f("该应用记录未表明应用已成功迁移, 无法确认")

        confirm_migration.delay(process.id)

        return Response(status=status.HTTP_204_NO_CONTENT)


class DefaultAppProcessViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """普通应用进程管理接口"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, *args, **kwargs):
        """list all processes/instances.

        用于直接从集群中获取应用进程信息(不依赖应用进程 db 数据)
        """
        wl_app = self._get_wl_app()
        processes_info = get_processes_info(wl_app)

        data = {
            "processes": {
                "items": processes_info.processes,
                "metadata": {"resource_version": processes_info.rv_proc},
            },
            "instances": {
                "items": [inst for proc in processes_info.processes for inst in proc.instances],
                "metadata": {"resource_version": processes_info.rv_inst},
            },
        }

        return Response(ListProcessesSLZ(data).data)

    def update(self, request, *args, **kwargs):
        """stop/start/scale process

        用于直接向集群中下发管理应用进程的命令(不涉及查询和更新应用进程的 db 数据)
        """
        slz = UpdateProcessSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        wl_app = self._get_wl_app()

        process_type = validated_data["process_type"]
        operate_type = validated_data["operate_type"]

        proc_config = get_mapper_proc_config_latest(wl_app, process_type)
        handler = ProcessesHandler.new_by_app(wl_app)

        try:
            if operate_type == ProcessUpdateType.START:
                handler.scale(proc_config, 1)
            elif operate_type == ProcessUpdateType.STOP:
                handler.shutdown(proc_config)
            else:
                target_replicas = validated_data["target_replicas"]
                handler.scale(proc_config, target_replicas)
        except Exception as e:
            raise wl_error_codes.PROCESS_OPERATE_FAILED.f(str(e))

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_wl_app(self):
        return WlAppBackupManager(self.get_env_via_path()).get()


class DefaultAppEntranceViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """普通应用访问地址查询接口"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def list_all_entrances(self, request, code):
        """查看应用所有模块的访问入口"""
        app = self.get_application()

        if last_process := CNativeMigrationProcess.objects.filter(
            app=app, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        ).last():
            return Response(data=ModuleEntrancesSLZ(last_process.legacy_data.entrances, many=True).data)

        return Response(data=[])
