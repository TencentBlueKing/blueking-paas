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
import json

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.constants import AppEnvName
from paasng.engine.deploy.infras import DeploymentCoordinator
from paasng.engine.deploy.preparations import initialize_deployment
from paasng.engine.deploy.runner import DeployTaskRunner
from paasng.engine.models import ConfigVar, Deployment
from paasng.engine.models.managers import DeployPhaseManager
from paasng.engine.streaming.constants import EventType
from paasng.extensions.bk_plugins import api_serializers, serializers
from paasng.extensions.bk_plugins.models import BkPluginTag, make_bk_plugin
from paasng.extensions.bk_plugins.tasks import archive_prod_env
from paasng.extensions.bk_plugins.views import logger
from paasng.metrics import DEPLOYMENT_INFO_COUNTER
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ApplicationMembership
from paasng.platform.applications.signals import application_member_updated, post_create_application
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.platform.applications.utils import create_application, create_default_module, create_market_config
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.utils.error_codes import error_codes

# TODO: 确认具体权限
API_PERMISSION_CLASSES = [IsAuthenticated, site_perm_class(SiteAction.SYSAPI_MANAGE_APPLICATIONS)]


class PluginInstanceViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """插件开发中心-插件实例相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.PluginSyncRequestSLZ,
        responses={201: serializers.BkPluginSLZ},
    )
    @atomic
    def create_plugin(self, request):
        slz = api_serializers.PluginSyncRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        region = settings.DEFAULT_REGION_NAME
        source_origin = SourceOrigin.AUTHORIZED_VCS
        encoded_operator = user_id_encoder.encode(
            getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), data["operator"]
        )

        application = create_application(
            region=region,
            code=data["id"],
            name=data["name_zh_cn"],
            name_en=data["name_en"],
            type_=ApplicationType.BK_PLUGIN,
            operator=encoded_operator,
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
            cluster_name=None,
        )

        application.language = module.language
        application.save(update_fields=['language'])

        post_create_application.send(sender=self.__class__, application=application)
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
        responses={200: serializers.BkPluginSLZ},
    )
    @atomic
    def update_plugin(self, request, code):
        application = self.get_application()

        slz = api_serializers.PluginSyncRequestSLZ(data=request.data)
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
        application = self.get_application()

        slz = api_serializers.PluginArchiveRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        encoded_operator = user_id_encoder.encode(
            getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), data["operator"]
        )

        # TODO: 停用插件网关(需要网关提供相应的接口)
        archive_prod_env.apply_async(args=(application.code, encoded_operator))
        return Response(data={})


class PluginDeployViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """插件开发中心-插件部署相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(
        tags=["plugin-center"],
        request_body=api_serializers.DeployPluginRequestSLZ,
        responses={201: api_serializers.PluginDeployResponseSLZ},
    )
    def deploy_plugin(self, request, code):
        """部署插件"""
        application = self.get_application()
        module = application.get_default_module()

        slz = api_serializers.DeployPluginRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        env = module.get_envs(environment=data["version"]["type"])
        coordinator = DeploymentCoordinator(env)
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_DEPLOY_ONGOING_EXISTS

        encoded_operator = user_id_encoder.encode(
            getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), data["operator"]
        )
        deployment = None
        try:
            with coordinator.release_on_error():
                deployment = initialize_deployment(
                    env=env,
                    operator=encoded_operator,
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
            steps.extend(phase.get_sorted_steps())

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
        application = self.get_application()
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
            steps.extend(phase.get_sorted_steps())

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
        application = self.get_application()
        try:
            deployment = Deployment.objects.get(pk=deploy_id, app_environment__module=application.get_default_module())
        except Deployment.DoesNotExist:
            raise error_codes.CANNOT_GET_DEPLOYMENT

        subscriber = StreamChannelSubscriber(deploy_id, redis_db=get_default_redis())
        channel_state = subscriber.get_channel_state()
        if channel_state == 'none' or channel_state == 'unknown':
            # redis 管道已结束, 取数据库中存储的日志
            return Response(
                data=api_serializers.PluginReleaseLogsResponseSLZ(
                    {"finished": True, "logs": deployment.logs.split("\n")}
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


class PluginMarketViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """插件开发中心-插件市场信息相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginMarketRequestSLZ)
    def upsert_market_info(self, request, code):
        application = self.get_application()
        profile = make_bk_plugin(application).get_profile()
        slz = api_serializers.PluginMarketRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        updated_data = {}
        for field in ["introduction", "contact"]:
            if data[field]:
                updated_data[field] = data[field]
        category = data["category"]
        if tag := BkPluginTag.objects.filter(name=category).first():
            updated_data["tag"] = tag

        serializer = serializers.BkPluginProfileSLZ(data=updated_data, instance=profile)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data={})

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.MarketCategorySLZ(many=True))
    def list_category(self, request):
        """查看系统中所有的“插件分类（Plugin-Tag）”，默认按照“创建时间（从旧到新）排序”"""
        tags = BkPluginTag.objects.all().order_by('created')
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


class PluginMembersViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """插件开发中心-成员管理相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginMemberSLZ(many=True))
    def sync_members(self, request, code):
        """同步插件成员"""
        application = self.get_application()

        slz = api_serializers.PluginMemberSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        members = []
        for member in data:
            user_id = user_id_encoder.encode(
                getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), username=member["username"]
            )
            ApplicationMembership.objects.update_or_create(
                defaults={"role": ApplicationRole(member["role"]["id"])},
                application=application,
                user=user_id,
            )
            members.append(user_id)
        # 删除用户
        ApplicationMembership.objects.filter(application=application).exclude(user__in=members).delete()
        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
        return Response(data={})


class PluginConfigurationViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """插件开发中心-配置管理相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginConfigSLZ(many=True))
    @atomic
    def sync_configurations(self, request, code):
        """同步插件配置(环境变量)"""
        application = self.get_application()
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
                },
            )
        # 删除多余的环境变量
        ConfigVar.objects.filter(module=module, environment=prod_env).exclude(
            key__in=[item["key"] for item in data]
        ).delete()
        return Response(data={})
