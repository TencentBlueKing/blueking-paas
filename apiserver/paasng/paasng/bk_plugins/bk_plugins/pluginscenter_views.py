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

import json
from collections import defaultdict
from contextlib import closing
from typing import Dict, List

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from django.conf import settings
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.bk_plugins.bk_plugins import api_serializers, serializers
from paasng.bk_plugins.bk_plugins.apigw import safe_update_gateway_status
from paasng.bk_plugins.bk_plugins.models import BkPluginTag, make_bk_plugin
from paasng.bk_plugins.bk_plugins.tasks import archive_prod_env
from paasng.bk_plugins.bk_plugins.views import logger
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.core.tenant.constants import AppTenantMode
from paasng.infras.iam.helpers import (
    add_role_members,
    delete_role_members,
    fetch_application_members,
    remove_user_all_roles,
)
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.metrics import DEPLOYMENT_INFO_COUNTER
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import application_member_updated, post_create_application
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.platform.applications.utils import create_application, create_default_module, create_market_config
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.deploy.start import DeployTaskRunner, initialize_deployment
from paasng.platform.engine.logs import get_all_logs
from paasng.platform.engine.models import ConfigVar, Deployment
from paasng.platform.engine.phases_steps.phases import DeployPhaseManager
from paasng.platform.engine.phases_steps.steps import get_sorted_steps
from paasng.platform.engine.streaming.constants import EventType
from paasng.platform.engine.workflow import DeploymentCoordinator
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.error_codes import error_codes

# TODO: 确认具体权限
API_PERMISSION_CLASSES = [sysapi_client_perm_class(ClientAction.MANAGE_APPLICATIONS)]


class PluginInstanceViewSet(viewsets.ViewSet):
    """插件开发中心-插件实例相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.PluginSyncRequestSLZ,
        responses={201: serializers.BkPluginSLZ()},
    )
    @atomic
    def create_plugin(self, request):
        slz = api_serializers.PluginSyncRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        source_origin = SourceOrigin.AUTHORIZED_VCS
        encoded_operator = user_id_encoder.encode(
            getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), data["operator"]
        )

        application = create_application(
            code=data["id"],
            name=data["name_zh_cn"],
            name_en=data["name_en"],
            app_type=ApplicationType.CLOUD_NATIVE,
            operator=encoded_operator,
            is_plugin_app=True,
            app_tenant_mode=AppTenantMode(data["plugin_tenant_mode"]),
            app_tenant_id=data["plugin_tenant_id"],
            tenant_id=data["tenant_id"],
        )

        module = create_default_module(
            application,
            source_init_template=data["template"]["id"],
            language=data["template"]["language"],
            source_origin=source_origin,
        )
        init_module_in_view(
            module,
            # TODO: 解决硬编码问题
            repo_type="tc_git",
            repo_url=data["repository"],
            repo_auth_info=None,
            source_dir="",
            env_cluster_names={},
        )

        application.language = module.language
        application.save(update_fields=["language"])

        post_create_application.send(sender=self.__class__, application=application, extra_fields=data["extra_fields"])
        create_market_config(
            application=application,
            # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
            # 对于新创建的应用, 如果集群支持 HTTPS, 则默认开启 HTTPS
            prefer_https=True,
        )
        return Response(status=status.HTTP_201_CREATED, data=serializers.BkPluginSLZ(make_bk_plugin(application)).data)

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.PluginSyncRequestSLZ,
        responses={200: serializers.BkPluginSLZ()},
    )
    @atomic
    def update_plugin(self, request, code):
        application = get_object_or_404(Application, code=code)

        slz = api_serializers.PluginSyncRequestSLZ(data=request.data, instance=application)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        application.name = data["name_zh_cn"]
        application.name_en = data["name_en"]
        application.save()
        return Response(data=serializers.BkPluginSLZ(make_bk_plugin(application)).data)

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.PluginArchiveRequestSLZ,
    )
    def archive_plugin(self, request, code):
        """下架插件 = 停用网关(切断流量入口) + 回收进程资源(异步)"""
        application = get_object_or_404(Application, code=code)

        slz = api_serializers.PluginArchiveRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        encoded_operator = user_id_encoder.encode(
            getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), data["operator"]
        )
        # 更新网关状态, 停用网关
        safe_update_gateway_status(application, enabled=False)
        archive_prod_env.apply_async(args=(application.code, encoded_operator))
        return Response(data={})


class PluginDeployViewSet(viewsets.ViewSet):
    """插件开发中心-插件部署相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.DeployPluginRequestSLZ,
        responses={201: api_serializers.PluginDeployResponseSLZ()},
    )
    def deploy_plugin(self, request, code):
        """部署插件"""
        application = get_object_or_404(Application, code=code)
        module = application.get_default_module()

        slz = api_serializers.DeployPluginRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        env = module.get_envs(environment=data["version"]["type"])
        coordinator = DeploymentCoordinator(env)
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_DEPLOY_ONGOING_EXISTS

        operator = user_id_encoder.encode(ProviderType.DATABASE, settings.PLUGIN_REPO_CONF["username"])
        deployment = None
        try:
            # 更新网关状态, 启用网关
            safe_update_gateway_status(application, enabled=True)
            with coordinator.release_on_error():
                deployment = initialize_deployment(
                    env=env,
                    operator=operator,
                    version_info=VersionInfo(
                        revision=data["version"]["source_hash"],
                        version_name=data["version"]["source_version_name"],
                        version_type=data["version"]["source_version_type"],
                    ),
                )
                coordinator.set_deployment(deployment)
                # Start a background deploy task
                DeployTaskRunner(deployment).start()
        except Exception as exception:
            DEPLOYMENT_INFO_COUNTER.labels(
                source_type=module.source_type, environment=AppEnvName.PROD, status="failed"
            ).inc()
            if deployment is not None:
                deployment.status = "failed"
                deployment.save(update_fields=["status", "updated"])
            logger.exception("Deploy request exception, please try again later")
            raise error_codes.CANNOT_DEPLOY_APP.f(_("部署请求异常，请稍候再试")) from exception

        DEPLOYMENT_INFO_COUNTER.labels(
            source_type=module.source_type, environment=env.environment, status="successful"
        ).inc()
        phases = DeployPhaseManager(env).get_or_create_all()
        steps = []
        for phase in phases:
            steps.extend(get_sorted_steps(phase))

        return Response(
            data=api_serializers.PluginDeployResponseSLZ(
                {"deploy_id": deployment.id, "status": deployment.status, "steps": steps}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        tags=["plugin-center"],
        responses={200: api_serializers.PluginDeployResponseSLZ},
    )
    def check_deploy_status(self, request, code, deploy_id):
        application = get_object_or_404(Application, code=code)
        try:
            deployment = Deployment.objects.get(pk=deploy_id, app_environment__module=application.get_default_module())
        except Deployment.DoesNotExist:
            raise error_codes.CANNOT_GET_DEPLOYMENT

        manager = DeployPhaseManager(deployment.app_environment)
        try:
            phases = [deployment.deployphase_set.get(type=type_) for type_ in manager.list_phase_types()]
        except Exception:
            logger.exception("failed to get phase info")
            raise error_codes.CANNOT_GET_DEPLOYMENT_PHASES

        steps = []
        for phase in phases:
            steps.extend(get_sorted_steps(phase))

        return Response(
            data=api_serializers.PluginDeployResponseSLZ(
                {
                    "deploy_id": deployment.id,
                    "status": deployment.status,
                    "steps": steps,
                    "detail": deployment.err_detail,
                }
            ).data,
        )

    @swagger_auto_schema(tags=["plugin-center"], responses={200: api_serializers.PluginReleaseLogsResponseSLZ})
    def get_deploy_logs(self, request, code, deploy_id):
        application = get_object_or_404(Application, code=code)
        try:
            deployment = Deployment.objects.get(pk=deploy_id, app_environment__module=application.get_default_module())
        except Deployment.DoesNotExist:
            raise error_codes.CANNOT_GET_DEPLOYMENT

        subscriber = StreamChannelSubscriber(deploy_id, redis_db=get_default_redis())

        with closing(subscriber):
            channel_state = subscriber.get_channel_state()
            if channel_state in ("none", "unknown"):
                # redis 管道已结束, 取数据库中存储的日志
                return Response(
                    data=api_serializers.PluginReleaseLogsResponseSLZ(
                        {"finished": True, "logs": get_all_logs(deployment).split("\n")}
                    ).data
                )

            logs = []
            finished = False
            events = subscriber.get_history_events(last_event_id=0, ignore_special=False)

        for event in events:
            if event["event"] == EventType.MSG.value:
                logs.append(json.loads(event["data"])["line"])
            if event["event"] == EventType.CLOSE.value:
                finished = True

        return Response(data=api_serializers.PluginReleaseLogsResponseSLZ({"finished": finished, "logs": logs}).data)


class PluginMarketViewSet(viewsets.ViewSet):
    """插件开发中心-插件市场信息相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginMarketRequestSLZ)
    def upsert_market_info(self, request, code):
        application = get_object_or_404(Application, code=code)
        profile = make_bk_plugin(application).get_profile()
        slz = api_serializers.PluginMarketRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        updated_data = {}

        if data["contact"]:
            updated_data["contact"] = data["contact"]
        if data["introduction"]:
            # introduction 为 lazy 对象直接放到 BkPluginProfileSLZ 中会报错
            updated_data["introduction"] = str(data["introduction"])

        category = data["category"]
        if tag := BkPluginTag.objects.filter(name=category).first():
            updated_data["tag"] = tag.id

        serializer = serializers.BkPluginProfileSLZ(data=updated_data, instance=profile)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data={})

    @swagger_auto_schema(
        tags=["plugin-center"], responses={status.HTTP_200_OK: api_serializers.MarketCategorySLZ(many=True)}
    )
    def list_category(self, request):
        """查看系统中所有的“插件分类（Plugin-Tag）”"""
        tags = BkPluginTag.objects.all()
        return Response(
            data=api_serializers.MarketCategorySLZ(
                [
                    {
                        "name": tag.name,
                        "value": tag.name,
                    }
                    for tag in tags
                ],
                many=True,
            ).data
        )


class PluginMembersViewSet(viewsets.ViewSet):
    """插件开发中心-成员管理相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginMemberSLZ(many=True))
    def sync_members(self, request, code):
        """同步插件成员"""
        application = get_object_or_404(Application, code=code)

        slz = api_serializers.PluginMemberSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        current_members = set()
        existed_members = {m["username"]: m for m in fetch_application_members(app_code=application.code)}
        need_to_add: Dict[ApplicationRole, List[str]] = defaultdict(list)  # Dict[role, usernames]
        need_to_clean: Dict[str, List[ApplicationRole]] = defaultdict(list)  # Dict[username, roles]
        for member in data:
            role = ApplicationRole(member["role"]["id"])
            username = member["username"]
            if username in existed_members and (redundant_roles := set(existed_members[username]["roles"]) - {role}):
                need_to_clean[username].extend(redundant_roles)
            need_to_add[role].append(username)
            current_members.add(username)

        # 删除用户
        if redundant_users := existed_members.keys() - current_members:
            remove_user_all_roles(app_code=application.code, usernames=list(redundant_users))
        # 添加用户权限
        for role, usernames in need_to_add.items():
            add_role_members(app_code=application.code, role=role, usernames=usernames)
        # 回收用户多余的权限
        for username, roles in need_to_clean.items():
            for role in roles:
                delete_role_members(app_code=application.code, role=role, usernames=[username])
        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
        return Response(data={})


class PluginConfigurationViewSet(viewsets.ViewSet):
    """插件开发中心-配置管理相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginConfigSLZ(many=True))
    @atomic
    def sync_configurations(self, request, code):
        """同步插件配置(环境变量)"""
        application = get_object_or_404(Application, code=code)
        module = application.get_default_module()
        prod_env = module.get_envs(AppEnvName.PROD)

        slz = api_serializers.PluginConfigSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        for item in data:
            ConfigVar.objects.update_or_create(
                module=module,
                environment=prod_env,
                key=item["key"],
                defaults={
                    "value": item["value"],
                    "description": item["description"],
                    "is_global": False,
                    "is_builtin": False,
                    "tenant_id": module.tenant_id,
                },
            )
        # 删除多余的环境变量
        ConfigVar.objects.filter(module=module, environment=prod_env).exclude(
            key__in=[item["key"] for item in data]
        ).delete()
        return Response(data={})
