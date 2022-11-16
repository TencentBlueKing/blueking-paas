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
import json
import logging
from collections import defaultdict
from typing import List, Tuple

from bkpaas_auth.core.encoder import ProviderType, user_id_encoder
from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from django.conf import settings
from django.db.transaction import atomic
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.iam.helpers import add_role_members, fetch_application_members, remove_user_all_roles
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class, site_perm_required
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.deploy.infras import DeploymentCoordinator
from paasng.engine.deploy.preparations import initialize_deployment
from paasng.engine.deploy.runner import DeployTaskRunner
from paasng.engine.models import Deployment
from paasng.engine.models.managers import DeployPhaseManager
from paasng.engine.streaming.constants import EventType
from paasng.metrics import DEPLOYMENT_INFO_COUNTER
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.signals import application_member_updated, post_create_application
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.platform.applications.utils import create_application, create_default_module, create_market_config
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.utils.error_codes import error_codes

from . import api_serializers, serializers
from .apigw import set_distributors
from .logging import PluginLoggingClient
from .models import (
    BkPlugin,
    BkPluginAppQuerySet,
    BkPluginDistributor,
    BkPluginTag,
    make_bk_plugin,
    make_bk_plugins,
    plugin_to_detailed,
)

logger = logging.getLogger(__name__)


class FilterPluginsMixin:
    """A mixin class which provides plugins filtering functionalities"""

    def filter_plugins(self, request: HttpRequest) -> Tuple[List[BkPlugin], LimitOffsetPagination]:
        """A reusable method for filtering plugins, with paginator supports.

        :param request: current Http request
        :param view: current view function,
        """
        serializer = serializers.ListBkPluginsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Query and paginate applications
        applications = BkPluginAppQuerySet().filter(
            search_term=data['search_term'],
            order_by=[data['order_by']],
            has_deployed=data['has_deployed'],
            distributor_code_name=data['distributor_code_name'],
            tag_id=data['tag_id'],
        )
        paginator = LimitOffsetPagination()
        applications = paginator.paginate_queryset(applications, request, self)

        plugins = make_bk_plugins(applications)
        return plugins, paginator


class SysBkPluginsViewset(FilterPluginsMixin, viewsets.ViewSet):
    """Viewset for bk_plugin type applications"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request):
        """查询所有的蓝鲸插件"""
        plugins, paginator = self.filter_plugins(request)
        return paginator.get_paginated_response(serializers.BkPluginSLZ(plugins, many=True).data)

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def retrieve(self, request, code):
        """查询某个蓝鲸插件的详细信息"""
        plugin = get_plugin_or_404(code)
        return Response(serializers.BkPluginDetailedSLZ(plugin_to_detailed(plugin)).data)


class SysBkPluginsBatchViewset(FilterPluginsMixin, viewsets.ViewSet):
    """Viewset for batch operations on bk_plugin type applications"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_detailed(self, request):
        """批量查询蓝鲸插件的详细信息（包含各环境部署状态等）"""
        plugins, paginator = self.filter_plugins(request)

        # Read extra params
        serializer = serializers.ListDetailedBkPluginsExtraSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        include_addresses = serializer.validated_data['include_addresses']

        results = [
            serializers.BkPluginDetailedSLZ(plugin_to_detailed(plugin, include_addresses)).data for plugin in plugins
        ]
        return paginator.get_paginated_response(results)


class SysBkPluginLogsViewset(viewsets.ViewSet):
    """Viewset for querying bk_plugin's logs"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request, code):
        """查询某个蓝鲸插件的结构化日志"""
        serializer = serializers.ListBkPluginLogsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = PluginLoggingClient(get_plugin_or_404(code))
        logs = client.query(data['trace_id'], data.get('scroll_id'))
        return Response(logs.dict())


def get_plugin_or_404(code: str) -> BkPlugin:
    """Get a bk_plugin object by code, raise 404 error when code is invalid

    :param code: plugin code, same with application code
    """
    application = get_object_or_404(BkPluginAppQuerySet().all(), code=code)
    return BkPlugin.from_application(application)


class SysBkPluginTagsViewSet(viewsets.ViewSet):
    """Viewset for querying bk_plugin's tags"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request):
        """View all plugin tags in the system, the default is based on "created time (from old to new)"""
        tags = BkPluginTag.objects.all().order_by('created')
        return Response(serializers.BkPluginTagSLZ(tags, many=True).data)


# User interface ViewSet start


class BkPluginProfileViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing BkPlugin's profile"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.BkPluginProfileSLZ})
    def retrieve(self, request, code):
        """获取一个蓝鲸插件的档案信息"""
        profile = self._get_plugin().get_profile()
        return Response(serializers.BkPluginProfileSLZ(instance=profile).data)

    @swagger_auto_schema(
        tags=["bk_plugin"],
        request_body=serializers.BkPluginProfileSLZ,
        responses={200: serializers.BkPluginProfileSLZ},
    )
    def patch(self, request, code):
        """修改蓝鲸插件的档案信息。接口使用补丁（patch）协议，支持每次只传递一个字段。"""
        profile = self._get_plugin().get_profile()
        serializer = serializers.BkPluginProfileSLZ(data=request.data, instance=profile)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializers.BkPluginProfileSLZ(instance=profile).data)

    def _get_plugin(self) -> BkPlugin:
        """Get BkPlugin object"""
        application = self.get_application()
        try:
            return make_bk_plugin(application)
        except TypeError:
            raise error_codes.APP_IS_NOT_BK_PLUGIN


class DistributorsViewSet(viewsets.ViewSet):
    """Viewset for plugin distributors"""

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.DistributorSLZ(many=True)})
    def list(self, request):
        """查看系统中所有的“插件使用方（Plugin-Distributor）”，默认按照“创建时间（从旧到新）排序”"""
        distributors = BkPluginDistributor.objects.all().order_by('created')
        return Response(serializers.DistributorSLZ(distributors, many=True).data)


class BkPluginTagsViewSet(viewsets.ViewSet):
    """Viewset for plugin tags"""

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.BkPluginTagSLZ(many=True)})
    def list(self, request):
        """查看系统中所有的“插件分类（Plugin-Tag）”，默认按照“创建时间（从旧到新）排序”"""
        tags = BkPluginTag.objects.all().order_by('created')
        return Response(serializers.BkPluginTagSLZ(tags, many=True).data)


class DistributorRelsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing a single bk_plugin's distributor relations"""

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.DistributorSLZ(many=True)})
    def list(self, request, code):
        """查看某个插件应用目前启用的“插件使用方”列表"""
        plugin_app = self.get_application()
        return Response(serializers.DistributorSLZ(plugin_app.distributors, many=True).data)

    @swagger_auto_schema(
        tags=["bk_plugin"],
        request_body=serializers.UpdateDistributorsSLZ,
        responses={200: serializers.DistributorSLZ(many=True)},
    )
    @atomic
    def update(self, request, code):
        """更新某个插件应用所启用的“插件使用方”列表"""
        serializer = serializers.UpdateDistributorsSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        plugin_app = self.get_application()
        distributors = serializer.validated_data['distributors']
        try:
            set_distributors(plugin_app, distributors)
        except RuntimeError:
            logger.exception(f'Unable to set distributor for {plugin_app}')
            raise error_codes.UNABLE_TO_SET_DISTRIBUTORS
        return Response(serializers.DistributorSLZ(plugin_app.distributors, many=True).data)


# User interface ViewSet end


class PluginCenterViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """a shim ViewSet for plugin-center to manage bk plugin"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.SYSAPI_MANAGE_APPLICATIONS)]

    @swagger_auto_schema(
        tags=["plugin-center"], request_body=api_serializers.PluginRequestSLZ, responses={201: serializers.BkPluginSLZ}
    )
    @atomic
    def create_plugin(self, request):
        slz = api_serializers.PluginRequestSLZ(data=request.data)
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
        request_body=api_serializers.PluginRequestSLZ,
        responses={200: serializers.BkPluginSLZ},
    )
    @atomic
    def update_plugin(self, request, code):
        application = self.get_application()

        slz = api_serializers.PluginRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        application.name = data["name_zh_cn"]
        application.name_en = data["name_en"]
        application.save()
        return Response(data=serializers.BkPluginSLZ(make_bk_plugin(application)).data)

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
                source_type=module.source_type, environment=self.kwargs["environment"], status="failed"
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
        if channel_state == 'none':
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

    @swagger_auto_schema(tags=["plugin-center"], request_body=api_serializers.PluginMemberSLZ(many=True))
    def sync_members(self, request, code):
        """同步插件成员"""
        application = self.get_application()

        slz = api_serializers.PluginMemberSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)

        # 清理掉旧的应用数据
        app_members = [member['username'] for member in fetch_application_members(app_code=application.code)]
        remove_user_all_roles(app_code=application.code, usernames=app_members)

        new_members = set()
        role_members = defaultdict(list)
        for member in slz.validated_data:
            username = member['username']
            role_members[ApplicationRole(member['role']['id'])].append(username)
            new_members.add(username)

        # 按照角色添加用户
        for role, members in role_members.items():
            add_role_members(app_code=application.code, role=role, usernames=members)

        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
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
