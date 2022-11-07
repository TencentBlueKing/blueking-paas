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
import cattr
import semver
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paasng.pluginscenter import constants, openapi_docs, serializers, shim
from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.filters import PluginInstancePermissionFilter
from paasng.pluginscenter.models import PluginDefinition, PluginInstance, PluginMarketInfo, PluginRelease
from paasng.pluginscenter.permissions import PluginInstanceOwnerPermission
from paasng.pluginscenter.sourcectl import build_master_placeholder, get_plugin_repo_accessor
from paasng.pluginscenter.thirdparty import market as market_api
from paasng.pluginscenter.thirdparty.instance import update_instance
from paasng.pluginscenter.thirdparty.log import query_standard_output_logs, query_structure_logs
from paasng.utils.api_docs import openapi_empty_schema
from paasng.utils.i18n import to_translated_field


class SchemaViewSet(ViewSet):
    @swagger_auto_schema(responses={200: openapi_docs.create_plugin_instance_schemas})
    def get_plugins_schema(self, request):
        """get plugin basic info schema for given PluginType"""
        schemas = []
        for pd in PluginDefinition.objects.all():
            basic_info_definition = pd.basic_info_definition
            schemas.append(
                {
                    "plugin_type": {
                        "id": pd.identifier,
                        "name": pd.name,
                        "description": pd.description,
                        "docs": pd.docs,
                        "logo": pd.logo,
                    },
                    "schema": {
                        "id": basic_info_definition.id_schema.dict(exclude_unset=True),
                        "name": basic_info_definition.name_schema.dict(exclude_unset=True),
                        "init_templates": cattr.unstructure(basic_info_definition.init_templates),
                        "release_method": basic_info_definition.release_method,
                        "repository_group": basic_info_definition.repository_group,
                        "repository_template": shim.build_repository_template(basic_info_definition.repository_group),
                        "extra_fields": cattr.unstructure(basic_info_definition.extra_fields),
                    },
                }
            )
        return Response(schemas)

    @swagger_auto_schema(responses={200: openapi_docs.market_schema})
    def get_market_schema(self, request, pd_id):
        """get market info schema for given PluginType"""
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        market_info_definition = pd.market_info_definition
        readonly = market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY
        return Response(
            {
                "category": market_api.list_category(pd) if not readonly else [],
                "schema": {
                    "extra_fields": cattr.unstructure(market_info_definition.extra_fields),
                },
                "readonly": readonly,
            }
        )

    @swagger_auto_schema(responses={200: openapi_docs.plugin_basic_info_schema})
    def get_basic_info_schema(self, request, pd_id):
        """get basic info schema for given PluginType"""
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        basic_info_definition = pd.basic_info_definition
        return Response(
            data={
                "id": basic_info_definition.id_schema.dict(exclude_unset=True),
                "name": basic_info_definition.name_schema.dict(exclude_unset=True),
                "extra_fields": cattr.unstructure(basic_info_definition.extra_fields),
            }
        )


class PluginInstanceMixin:
    def get_plugin_instance(self) -> PluginInstance:
        queryset = PluginInstance.objects.all()
        filter_kwargs = {"pd__identifier": self.kwargs["pd_id"], "id": self.kwargs["plugin_id"]}  # type: ignore
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)  # type: ignore
        return obj


class PluginInstanceViewSet(PluginInstanceMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = PluginInstance.objects.all()
    serializer_class = serializers.PluginInstanceSLZ
    pagination_class = LimitOffsetPagination
    filter_backends = [PluginInstancePermissionFilter, OrderingFilter, SearchFilter]
    permission_classes = [IsAuthenticated, PluginInstanceOwnerPermission]
    search_fields = ["id", "name_zh_cn", "name_en", "language", "pd__name", "pd__identifier", "status"]

    @atomic
    @swagger_auto_schema(request_body=serializers.StubCreatePluginSLZ)
    def create(self, request, pd_id, **kwargs):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = serializers.make_plugin_slz_class(pd, creation=True)(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        plugin = PluginInstance(
            pd=pd,
            language=validated_data["template"].language,
            **validated_data,
            creator=request.user.pk,
        )
        plugin.save()
        plugin.refresh_from_db()
        shim.init_plugin_in_view(plugin, request.user.pk)
        return Response(
            data=self.get_serializer(plugin).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        return Response(data=self.get_serializer(plugin).data)

    @atomic
    @swagger_auto_schema(request_body=serializers.StubUpdatePluginSLZ)
    def update(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = serializers.make_plugin_slz_class(pd, creation=False)(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # TODO: editable
        plugin.name = validated_data[to_translated_field("name")]
        plugin.extra_fields = validated_data["extra_fields"]
        plugin.save()
        if pd.basic_info_definition.api.update:
            update_instance(pd, plugin, operator=request.user.pk)
        return Response(data=self.get_serializer(plugin).data)


class PluginReleaseViewSet(PluginInstanceMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = serializers.PluginReleaseVersionSLZ
    pagination_class = LimitOffsetPagination
    filter_backends = [OrderingFilter, SearchFilter]
    permission_classes = [IsAuthenticated, PluginInstanceOwnerPermission]
    search_fields = ["version", "source_version_name", "source_hash", "status"]

    @atomic
    @swagger_auto_schema(
        request_body=serializers.StubCreatePluginReleaseVersionSLZ,
        responses={201: serializers.PluginReleaseVersionSLZ},
    )
    def create(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        if plugin.all_versions.filter(
            status__in=[constants.PluginReleaseStatus.INITIAL, constants.PluginReleaseStatus.PENDING]
        ):
            raise error_codes.CANNOT_RELEASE_ONGOING_EXISTS

        version_type = request.data["source_version_type"]
        version_name = request.data["source_version_name"]
        source_hash = get_plugin_repo_accessor(plugin).extract_smart_revision(f"{version_type}:{version_name}")

        slz = serializers.make_create_release_version_slz_class(plugin.pd)(
            data=request.data,
            context={
                "source_hash": source_hash,
                "previous_version": getattr(plugin.all_versions.get_latest_succeeded(), "version", None),
            },
        )
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        release = PluginRelease.objects.create(
            plugin=plugin, source_location=plugin.repository, source_hash=source_hash, **data
        )
        release.initial_stage_set()
        shim.execute_stage(release.current_stage, request.user.pk)
        release.status = constants.PluginReleaseStatus.PENDING
        release.save()
        return Response(data=self.get_serializer(release).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pd_id, plugin_id, release_id):
        release = self.get_queryset().get(pk=release_id)
        return Response(data=self.get_serializer(release).data)

    @atomic
    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def enter_next_stage(self, request, pd_id, plugin_id, release_id):
        release = self.get_queryset().get(pk=release_id)
        shim.enter_next_stage(release.current_stage, request.user.pk)
        release.refresh_from_db()
        return Response(data=self.get_serializer(release).data)

    @atomic
    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def cancel_release(self, request, pd_id, plugin_id, release_id):
        release = self.get_queryset().get(pk=release_id)
        release.all_stages.update(status=constants.PluginReleaseStatus.INTERRUPTED, fail_message="用户主动终止发布")
        release.status = constants.PluginReleaseStatus.INTERRUPTED
        release.save()
        return Response(data=self.get_serializer(release).data)

    @swagger_auto_schema(responses={200: openapi_docs.create_release_schema})
    def get_release_schema(self, request, pd_id, plugin_id):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        plugin = self.get_plugin_instance()
        release_revision = pd.release_revision
        if release_revision.revisionType == "master":
            versions = [build_master_placeholder()]
        elif release_revision.revisionType == "tag":
            versions = get_plugin_repo_accessor(plugin).list_alternative_versions(
                include_branch=False, include_tag=True
            )
        else:
            versions = get_plugin_repo_accessor(plugin).list_alternative_versions(
                include_branch=True, include_tag=True
            )

        semver_choices = None
        current_release = plugin.all_versions.get_latest_succeeded()
        if release_revision.versionNo == constants.PluginReleaseVersionRule.AUTOMATIC:
            current_version_no = semver.VersionInfo.parse(getattr(current_release, "version", "0.0.0"))
            semver_choices = {
                constants.SemverAutomaticType.MAJOR: str(current_version_no.bump_major()),
                constants.SemverAutomaticType.MINOR: str(current_version_no.bump_minor()),
                constants.SemverAutomaticType.PATCH: str(current_version_no.bump_patch()),
            }

        return Response(
            {
                "docs": release_revision.docs,
                "source_version_pattern": release_revision.revisionPattern,
                "version_no": release_revision.versionNo,
                "extra_fields": cattr.unstructure(release_revision.extraFields),
                "source_versions": cattr.unstructure(versions),
                "semver_choices": semver_choices,
                "current_release": serializers.PlainPluginReleaseVersionSLZ(current_release).data
                if current_release
                else None,
            }
        )

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return PluginRelease.objects.none()
        plugin = self.get_plugin_instance()
        qs = PluginRelease.objects.filter(plugin=plugin).order_by("-created")
        return qs


class PluginReleaseStageViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, PluginInstanceOwnerPermission]

    def retrieve(self, request, pd_id, plugin_id, release_id, stage_id):
        plugin = self.get_plugin_instance()
        release = plugin.all_versions.get(pk=release_id)
        stage = release.all_stages.get(stage_id=stage_id)
        return Response(data=shim.render_release_stage(stage))


class PluginMarketViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, PluginInstanceOwnerPermission]
    serializer_class = serializers.PluginMarketInfoSLZ

    def retrieve(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        pd = plugin.pd
        if pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY:
            market_info = market_api.read_market_info(pd, plugin)
        else:
            market_info = plugin.pluginmarketinfo
        return Response(data=self.get_serializer(market_info).data)

    @atomic
    @swagger_auto_schema(
        request_body=serializers.StubUpsertMarketInfoSLZ,
    )
    def upsert(self, request, pd_id, plugin_id):
        """创建/更新市场信息"""
        plugin = self.get_plugin_instance()
        pd = plugin.pd

        slz = serializers.make_market_info_slz_class(pd)(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        market_info, created = PluginMarketInfo.objects.update_or_create(
            defaults=data,
            plugin=plugin,
        )
        if pd.market_info_definition.storage != constants.MarketInfoStorageType.PLATFORM:
            if created:
                market_api.create_market_info(pd, plugin, market_info, operator=request.user.pk)
            else:
                market_api.update_market_info(pd, plugin, market_info, operator=request.user.pk)
        # 如果当前插件正处于完善市场信息的发布阶段, 则设置该阶段的状态为 successful(允许进入下一阶段)
        if release := plugin.all_versions.get_ongoing_release():
            if release.current_stage and release.current_stage.stage_id == "market":
                release.current_stage.status = constants.PluginReleaseStatus.SUCCESSFUL
                release.current_stage.save()
        return Response(data=self.get_serializer(market_info).data)


class PluginLogViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, PluginInstanceOwnerPermission]

    @swagger_auto_schema(
        query_serializer=serializers.PluginLogQueryParamsSLZ,
        request_body=serializers.PluginLogQueryBodySLZ,
        responses={200: serializers.StandardOutputLogsSLZ},
    )
    def query_standard_output_logs(self, request, pd_id, plugin_id):
        """查询标准输出日志"""
        plugin = self.get_plugin_instance()

        slz = serializers.PluginLogQueryBodySLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slz = serializers.PluginLogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        logs = query_standard_output_logs(
            pd=plugin.pd,
            instance=plugin,
            operator=request.user.pk,
            time_range=query_params["smart_time_range"],
            query_string=data["query_string"],
            limit=query_params["limit"],
            offset=query_params["offset"],
        )
        return Response(data=serializers.StandardOutputLogsSLZ(logs).data)

    @swagger_auto_schema(
        query_serializer=serializers.PluginLogQueryParamsSLZ,
        request_body=serializers.PluginLogQueryBodySLZ,
        responses={200: serializers.StructureLogsSLZ},
    )
    def query_structure_logs(self, request, pd_id, plugin_id):
        """查询结构化日志"""
        plugin = self.get_plugin_instance()

        slz = serializers.PluginLogQueryBodySLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slz = serializers.PluginLogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        logs = query_structure_logs(
            pd=plugin.pd,
            instance=plugin,
            operator=request.user.pk,
            time_range=query_params["smart_time_range"],
            query_string=data["query_string"],
            limit=query_params["limit"],
            offset=query_params["offset"],
        )
        return Response(data=serializers.StructureLogsSLZ(logs).data)
