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
import logging
from typing import Dict, List, Literal

import cattr
import semver
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paasng.bk_plugins.pluginscenter import constants
from paasng.bk_plugins.pluginscenter import log as log_api
from paasng.bk_plugins.pluginscenter import openapi_docs, serializers, shim
from paasng.bk_plugins.pluginscenter.bk_devops.client import BkDevopsClient
from paasng.bk_plugins.pluginscenter.bk_devops.exceptions import BkDevopsApiError, BkDevopsGatewayServiceError
from paasng.bk_plugins.pluginscenter.bk_devops.utils import get_devops_project_id
from paasng.bk_plugins.pluginscenter.configuration import PluginConfigManager
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.features import PluginFeatureFlag, PluginFeatureFlagsManager
from paasng.bk_plugins.pluginscenter.filters import PluginInstancePermissionFilter
from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import PluginPermissionActions as Actions
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as members_api
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.permissions import plugin_action_permission_class
from paasng.bk_plugins.pluginscenter.itsm_adaptor.utils import submit_create_approval_ticket
from paasng.bk_plugins.pluginscenter.models import (
    OperationRecord,
    PluginBasicInfoDefinition,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfo,
    PluginRelease,
)
from paasng.bk_plugins.pluginscenter.permissions import IsPluginCreator, PluginCenterFeaturePermission
from paasng.bk_plugins.pluginscenter.releases.executor import PluginReleaseExecutor, init_stage_controller
from paasng.bk_plugins.pluginscenter.sourcectl import (
    build_master_placeholder,
    get_plugin_repo_accessor,
    get_plugin_repo_member_maintainer,
    remove_repo_member,
)
from paasng.bk_plugins.pluginscenter.thirdparty import instance as instance_api
from paasng.bk_plugins.pluginscenter.thirdparty import market as market_api
from paasng.bk_plugins.pluginscenter.thirdparty.configuration import sync_config
from paasng.bk_plugins.pluginscenter.thirdparty.instance import update_instance
from paasng.bk_plugins.pluginscenter.thirdparty.members import sync_members
from paasng.utils.api_docs import openapi_empty_schema
from paasng.utils.i18n import to_translated_field
from paasng.utils.views import permission_classes as _permission_classes

logger = logging.getLogger(__name__)


class SchemaViewSet(ViewSet):
    @swagger_auto_schema(responses={200: openapi_docs.create_plugin_instance_schemas})
    def get_plugins_schema(self, request):
        """get plugin basic info schema for given PluginType"""
        schemas = []
        for pd in PluginDefinition.objects.all():
            basic_info_definition = pd.basic_info_definition
            pd_data = serializers.PluginDefinitionSLZ(pd).data
            schemas.append(
                {
                    "plugin_type": pd_data,
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

    @swagger_auto_schema(responses={200: serializers.PluginConfigSchemaSLZ()})
    def get_config_schema(self, request, pd_id):
        """get config schema for given PluginType"""
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        config_definition = pd.config_definition
        return Response(data=serializers.PluginConfigSchemaSLZ(config_definition).data)


class PluginInstanceMixin:
    """PluginInstanceMixin provide a shortcut method to get a plugin instance

    IF request.user DOES NOT have object permissions, will raise PermissionDeny exception
    """

    def get_plugin_instance(self, allow_archive: bool = True) -> PluginInstance:
        queryset = PluginInstance.objects.all()
        filter_kwargs = {"pd__identifier": self.kwargs["pd_id"], "id": self.kwargs["plugin_id"]}  # type: ignore
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)  # type: ignore
        if not allow_archive and obj.status in constants.PluginStatus.archive_status():
            raise error_codes.PLUGIN_ARCHIVED
        return obj


class PluginInstanceViewSet(PluginInstanceMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = PluginInstance.objects.all()
    serializer_class = serializers.PluginInstanceSLZ
    pagination_class = LimitOffsetPagination
    filter_backends = [PluginInstancePermissionFilter, OrderingFilter, SearchFilter]
    search_fields = ["id", "name_zh_cn", "name_en"]
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        slz = serializers.PluginListFilterSlZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        if status_list := query_params.get('status', []):
            queryset = queryset.filter(status__in=status_list)

        if language_list := query_params.get('language', []):
            queryset = queryset.filter(language__in=language_list)

        if pd__identifier_list := query_params.get('pd__identifier', []):
            queryset = queryset.filter(pd__identifier__in=pd__identifier_list)
        return queryset

    @atomic
    @swagger_auto_schema(request_body=serializers.StubCreatePluginSLZ)
    @_permission_classes([IsAuthenticated, PluginCenterFeaturePermission])
    def create(self, request, pd_id, **kwargs):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = serializers.make_plugin_slz_class(pd, creation=True)(data=request.data, context={"pd": pd})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        plugin_status = (
            constants.PluginStatus.WAITING_APPROVAL
            if pd.approval_config.enabled
            else constants.PluginStatus.DEVELOPING
        )
        plugin = PluginInstance(
            pd=pd,
            language=validated_data["template"].language,
            **validated_data,
            creator=request.user.pk,
            # 如果插件不需要审批，则状态设置为开发中
            status=plugin_status,
        )
        plugin.save()
        plugin.refresh_from_db()

        # 如果插件需要审批则需要创建审批流程，审批通过后才初始化插件信息
        if pd.approval_config.enabled:
            submit_create_approval_ticket(pd, plugin, request.user.username)
        else:
            shim.init_plugin_in_view(plugin, request.user.username)

        # 操作记录: 创建插件
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.CREATE,
            subject=constants.SubjectTypes.PLUGIN,
        )
        return Response(
            data=self.get_serializer(plugin).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance(allow_archive=True)
        return Response(data=self.get_serializer(plugin).data)

    @atomic
    @swagger_auto_schema(request_body=serializers.StubUpdatePluginSLZ)
    @_permission_classes(
        [
            IsAuthenticated,
            PluginCenterFeaturePermission,
            plugin_action_permission_class([Actions.BASIC_DEVELOPMENT, Actions.EDIT_PLUGIN]),
        ]
    )
    def update(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = serializers.make_plugin_slz_class(pd, creation=False)(data=request.data, context={"pd": pd})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # TODO: editable
        plugin.name = validated_data[to_translated_field("name")]
        plugin.extra_fields = validated_data["extra_fields"]
        plugin.save()
        if pd.basic_info_definition.api.update:
            update_instance(pd, plugin, operator=request.user.pk)

        # 操作记录: 修改基本信息
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.MODIFY,
            subject=constants.SubjectTypes.BASIC_INFO,
        )
        return Response(data=self.get_serializer(plugin).data)

    @atomic
    @swagger_auto_schema(request_body=serializers.PluginInstanceLogoSLZ)
    @_permission_classes(
        [
            IsAuthenticated,
            PluginCenterFeaturePermission,
            plugin_action_permission_class([Actions.BASIC_DEVELOPMENT, Actions.EDIT_PLUGIN]),
        ]
    )
    def update_logo(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = serializers.PluginInstanceLogoSLZ(data=request.data, instance=plugin)
        slz.is_valid(raise_exception=True)
        slz.save()
        if pd.basic_info_definition.api.update:
            update_instance(pd, plugin, operator=request.user.pk)

        # 操作记录: 修改 logo
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.MODIFY,
            subject=constants.SubjectTypes.LOGO,
        )
        return Response(data=self.get_serializer(plugin).data)

    @atomic
    @_permission_classes([IsAuthenticated, PluginCenterFeaturePermission, IsPluginCreator])
    def destroy(self, request, pd_id, plugin_id):
        """仅创建审批失败的插件可删除"""
        plugin = self.get_plugin_instance()
        # 仅创建失败的状态的插件可删除
        if plugin.status != constants.PluginStatus.APPROVAL_FAILED:
            raise error_codes.CANNOT_BE_DELETED

        plugin.delete()
        logger.error(f"plugin(id: {plugin_id}) is deleted by {request.user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @_permission_classes(
        [IsAuthenticated, PluginCenterFeaturePermission, plugin_action_permission_class([Actions.DELETE_PLUGIN])]
    )
    def archive(self, request, pd_id, plugin_id):
        """插件下架"""
        plugin = self.get_plugin_instance()
        instance_api.archive_instance(plugin.pd, plugin, operator=request.user.username)
        # 操作记录: 插件下架
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.ARCHIVE,
            subject=constants.SubjectTypes.PLUGIN,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_filter_params(self, request):
        """Get plug-in list filtering parameters, such as plug-in type, development language, etc."""
        pds = PluginDefinition.objects.all()
        return Response(
            data={
                "plugin_types": serializers.PluginDefinitionBasicSLZ(pds, many=True).data,
                "languages": PluginBasicInfoDefinition.get_languages(),
            }
        )

    @swagger_auto_schema(query_serializer=serializers.CodeCommitSearchSLZ)
    def get_code_submit_info(self, request, pd_id, plugin_id):
        """插件代码库的提交信息"""
        slz = serializers.CodeCommitSearchSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        _data = slz.validated_data

        plugin = self.get_plugin_instance()
        repo_accessor = get_plugin_repo_accessor(plugin)
        return Response(data=repo_accessor.get_submit_info(_data['begin_time'], _data['end_time']))

    def get_feature_flags(self, request, pd_id, plugin_id):
        """获取插件支持的功能特性"""
        plugin = self.get_plugin_instance()
        return Response(data=PluginFeatureFlagsManager(plugin).list_all_features())

    @swagger_auto_schema(responses={200: serializers.MetricsSummarySLZ})
    def get_repo_overview(self, request, pd_id, plugin_id):
        """插件代码仓库的概览信息"""
        plugin = self.get_plugin_instance()

        # 获取代码仓库对应的蓝盾项目 ID
        repo_accessor = get_plugin_repo_accessor(plugin)
        project_id = repo_accessor.get_project_id()
        devops_project_id = get_devops_project_id(project_id)

        client = BkDevopsClient(request.user.username)
        try:
            summary = client.get_metrics_summary(devops_project_id)
        except (BkDevopsApiError, BkDevopsGatewayServiceError):
            # TODO 蓝盾API 还在灰度中，先不抛错误异常
            # raise error_codes.QUERY_REPO_OVERVIEW_DATA_ERROR
            return Response(data={})

        return Response(data=serializers.MetricsSummarySLZ(summary).data)


class OperationRecordViewSet(PluginInstanceMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = OperationRecord.objects.all().order_by('-created')
    serializer_class = serializers.OperationRecordSLZ
    pagination_class = LimitOffsetPagination
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]

    def get_queryset(self):
        plugin = self.get_plugin_instance()
        return self.queryset.filter(plugin=plugin)


@method_decorator(
    _permission_classes(
        [IsAuthenticated, PluginCenterFeaturePermission, plugin_action_permission_class([Actions.BASIC_DEVELOPMENT])]
    ),
    name="list",
)
class PluginReleaseViewSet(PluginInstanceMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = serializers.PluginReleaseVersionSLZ
    pagination_class = LimitOffsetPagination
    filter_backends = [OrderingFilter, SearchFilter]
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]
    search_fields = ["version", "source_version_name"]
    ordering = ('-created',)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        slz = serializers.PluginReleaseFilterSLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        if status_list := query_params.get('status', []):
            queryset = queryset.filter(status__in=status_list)
        return queryset

    def retrieve(self, request, pd_id, plugin_id, release_id):
        release = self.get_queryset().get(pk=release_id)
        return Response(data=self.get_serializer(release).data)

    def get_compare_url(self, request, pd_id, plugin_id, from_revision, to_revision):
        plugin = self.get_plugin_instance()
        repo_accessor = get_plugin_repo_accessor(plugin)
        compare_url = repo_accessor.build_compare_url(from_revision, to_revision)
        return Response({"result": compare_url})

    @atomic
    @swagger_auto_schema(
        request_body=serializers.StubCreatePluginReleaseVersionSLZ,
        responses={201: serializers.PluginReleaseVersionSLZ},
    )
    @_permission_classes(
        [
            IsAuthenticated,
            PluginCenterFeaturePermission,
            plugin_action_permission_class([Actions.BASIC_DEVELOPMENT, Actions.RELEASE_VERSION]),
        ]
    )
    def create(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance()
        if plugin.all_versions.filter(status__in=constants.PluginReleaseStatus.running_status()).exists():
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
            plugin=plugin, source_location=plugin.repository, source_hash=source_hash, creator=request.user.pk, **data
        )
        PluginReleaseExecutor(release).initial(operator=request.user.username)

        # 如果插件的状态不是已发布，则更新为发布中
        if plugin.status != constants.PluginStatus.RELEASED:
            plugin.status = constants.PluginStatus.RELEASING
            plugin.save()

        # 操作记录: 新建 xx 版本
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.ADD,
            specific=release.version,
            subject=constants.SubjectTypes.VERSION,
        )
        release.refresh_from_db()
        return Response(data=self.get_serializer(release).data, status=status.HTTP_201_CREATED)

    @atomic
    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def enter_next_stage(self, request, pd_id, plugin_id, release_id):
        """进入下一发布步骤"""
        release = self.get_queryset().get(pk=release_id)
        PluginReleaseExecutor(release).enter_next_stage(operator=request.user.username)
        release.refresh_from_db()
        return Response(data=self.get_serializer(release).data)

    @atomic
    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def back_to_previous_stage(self, request, pd_id, plugin_id, release_id):
        """返回上一发布步骤, 重置当前步骤和上一步骤的执行状态, 并重新执行上一步。"""
        plugin = self.get_plugin_instance()
        if (
            plugin.all_versions.filter(status__in=constants.PluginReleaseStatus.running_status())
            .exclude(pk=release_id)
            .exists()
        ):
            raise error_codes.CANNOT_RELEASE_ONGOING_EXISTS
        release = self.get_queryset().get(pk=release_id)
        PluginReleaseExecutor(release).back_to_previous_stage(operator=request.user.username)
        release.refresh_from_db()
        return Response(data=self.get_serializer(release).data)

    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def re_release(self, request, pd_id, plugin_id, release_id):
        """重新发布版本"""
        plugin = self.get_plugin_instance()
        if plugin.all_versions.filter(status__in=constants.PluginReleaseStatus.running_status()).exists():
            raise error_codes.CANNOT_RELEASE_ONGOING_EXISTS

        release = self.get_queryset().get(pk=release_id)
        PluginReleaseExecutor(release).reset_release(operator=request.user.username)

        # 操作记录: 重新发布 xx 版本
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.RE_RELEASE,
            specific=release.version,
            subject=constants.SubjectTypes.VERSION,
        )
        release.refresh_from_db()
        return Response(data=self.get_serializer(release).data)

    @atomic
    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def cancel_release(self, request, pd_id, plugin_id, release_id):
        """取消发布"""
        plugin = self.get_plugin_instance()
        # 插件可设置不能取消发布的特性
        if not PluginFeatureFlagsManager(plugin).has_feature(PluginFeatureFlag.CANCEL_RELEASE):
            raise error_codes.NOT_SUPPORT_CANCEL_RELEASE.f(_("插件不支持终止发布操作"))

        release = self.get_queryset().get(pk=release_id)
        PluginReleaseExecutor(release).cancel_release(operator=request.user.username)

        # 操作记录: 终止发布 xx 版本
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.TERMINATE,
            specific=release.version,
            subject=constants.SubjectTypes.VERSION,
        )
        release.refresh_from_db()
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
        plugin = self.get_plugin_instance(allow_archive=True)
        qs = PluginRelease.objects.filter(plugin=plugin).order_by("-created")
        return qs


class PluginReleaseStageViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]

    def retrieve(self, request, pd_id, plugin_id, release_id, stage_id):
        plugin = self.get_plugin_instance(allow_archive=True)
        release = plugin.all_versions.get(pk=release_id)
        stage = release.all_stages.get(stage_id=stage_id)
        return Response(data=init_stage_controller(stage).render_to_view())

    @swagger_auto_schema(request_body=openapi_empty_schema, responses={200: serializers.PluginReleaseVersionSLZ})
    def rerun(self, request, pd_id, plugin_id, release_id, stage_id):
        """重新执行发布步骤"""
        plugin = self.get_plugin_instance()
        release = plugin.all_versions.get(pk=release_id)
        if release.current_stage.stage_id != stage_id:
            raise error_codes.CANNOT_RERUN_ONGOING_STEPS.f(_("仅支持重试当前阶段"))

        PluginReleaseExecutor(release).rerun_current_stage(operator=request.user.username)
        stage = release.all_stages.get(stage_id=stage_id)
        return Response(data=init_stage_controller(stage).render_to_view())


class PluginMarketViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]
    serializer_class = serializers.PluginMarketInfoSLZ

    def retrieve(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance(allow_archive=True)
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
                release.current_stage.update_status(constants.PluginReleaseStatus.SUCCESSFUL)

        # 操作记录: 修改市场信息
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.MODIFY,
            subject=constants.SubjectTypes.MARKET_INFO,
        )
        return Response(data=self.get_serializer(market_info).data)


class PluginMembersViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT, Actions.MANAGE_MEMBERS]),
    ]
    serializer_class = serializers.PluginMemberSLZ

    @_permission_classes(
        [IsAuthenticated, PluginCenterFeaturePermission, plugin_action_permission_class([Actions.BASIC_DEVELOPMENT])]
    )
    def list(self, request, pd_id, plugin_id):
        plugin = self.get_plugin_instance(allow_archive=True)
        members = members_api.fetch_plugin_members(plugin)
        return Response(data=self.get_serializer(members, many=True).data)

    @swagger_auto_schema(request_body=openapi_empty_schema)
    @_permission_classes(
        [IsAuthenticated, PluginCenterFeaturePermission, plugin_action_permission_class([Actions.BASIC_DEVELOPMENT])]
    )
    def leave(self, request, pd_id, plugin_id):
        """用户主动退出插件成员的API"""
        plugin = self.get_plugin_instance()
        self._check_admin_count(plugin, [request.user.username])
        remove_repo_member(plugin, request.user.username)
        members_api.remove_user_all_roles(plugin=plugin, usernames=[request.user.username])
        sync_members(pd=plugin.pd, instance=plugin)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={201: openapi_empty_schema}, request_body=serializers.PluginMemberSLZ(many=True))
    def create(self, request, pd_id, plugin_id):
        """新增插件成员"""
        plugin = self.get_plugin_instance()
        slz = self.get_serializer(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        cur_users = {member.username for member in members_api.fetch_plugin_members(plugin)}
        to_add_users = set()

        grouped: Dict[constants.PluginRole, List[str]] = {
            constants.PluginRole.ADMINISTRATOR: [],
            constants.PluginRole.DEVELOPER: [],
        }
        for item in data:
            grouped[item["role"]["id"]].append(item["username"])
            to_add_users.add(item["username"])

        # 检测用户是否已存在, 存在则报错
        if conflict_users := cur_users & to_add_users:
            raise error_codes.MEMBERSHIP_ADD_FAILED.f(_("用户 {} 已存在").format(sorted(conflict_users)))

        repo_member_maintainer = get_plugin_repo_member_maintainer(plugin)
        if usernames := grouped[constants.PluginRole.DEVELOPER]:
            self._check_admin_count(plugin, usernames)
            for username in usernames:
                repo_member_maintainer.add_member(username, constants.PluginRole.DEVELOPER)
            members_api.add_role_members(plugin, role=constants.PluginRole.DEVELOPER, usernames=usernames)
            members_api.delete_role_members(plugin, role=constants.PluginRole.ADMINISTRATOR, usernames=usernames)
        elif usernames := grouped[constants.PluginRole.ADMINISTRATOR]:
            for username in usernames:
                repo_member_maintainer.add_member(username, constants.PluginRole.ADMINISTRATOR)
            members_api.add_role_members(plugin, role=constants.PluginRole.ADMINISTRATOR, usernames=usernames)
            members_api.delete_role_members(plugin, role=constants.PluginRole.DEVELOPER, usernames=usernames)
        sync_members(pd=plugin.pd, instance=plugin)
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={201: openapi_empty_schema}, request_body=serializers.PluginRoleSLZ)
    def update_role(self, request, pd_id, plugin_id, username: str):
        """更换角色"""
        plugin = self.get_plugin_instance()
        slz = serializers.PluginRoleSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        to_role_id = constants.PluginRole(data["id"])
        user_roles = members_api.fetch_user_roles(plugin, username)
        if len(user_roles) == 0:
            raise error_codes.MEMBERSHIP_UPDATE_FAILED.f(_("插件成员 {} 不存在".format(username)))

        if to_role_id != constants.PluginRole.ADMINISTRATOR:
            self._check_admin_count(plugin, [username])

        # 由于权限中心的特性, 用户可以同时在多个用户组.
        # 因此更换角色的流程分为 2 步:
        # 1. 添加角色至用户组
        repo_member_maintainer = get_plugin_repo_member_maintainer(plugin)
        repo_member_maintainer.add_member(username, to_role_id)
        members_api.add_role_members(plugin, role=to_role_id, usernames=[username])

        # 2. 删除角色的其他用户组
        for role_id in user_roles:
            if role_id == to_role_id:
                continue
            members_api.delete_role_members(plugin, role=role_id, usernames=[username])
        sync_members(pd=plugin.pd, instance=plugin)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={204: openapi_empty_schema})
    def destroy(self, request, pd_id, plugin_id, username: str):
        plugin = self.get_plugin_instance()
        self._check_admin_count(plugin, [username])
        remove_repo_member(plugin, username)
        members_api.remove_user_all_roles(plugin=plugin, usernames=[username])
        sync_members(pd=plugin.pd, instance=plugin)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _check_admin_count(self, plugin: PluginInstance, blacklist: List[str]):
        """检测管理员数量, 避免移除人员后插件无管理员"""
        admins = {
            member.username
            for member in members_api.fetch_plugin_members(plugin)
            if member.role.id == constants.PluginRole.ADMINISTRATOR
        }
        if len(admins - set(blacklist)) < 1:
            raise error_codes.MEMBERSHIP_DELETE_FAILED


class PluginLogViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.BASIC_DEVELOPMENT]),
    ]

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

        logs = log_api.query_standard_output_logs(
            pd=plugin.pd,
            instance=plugin,
            operator=request.user.username,
            time_range=query_params["smart_time_range"],
            query_string=data["query"]["query_string"],
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

        logs = log_api.query_structure_logs(
            pd=plugin.pd,
            instance=plugin,
            operator=request.user.username,
            time_range=query_params["smart_time_range"],
            query_string=data["query"]["query_string"],
            terms=data["query"]["terms"],
            exclude=data["query"]["exclude"],
            limit=query_params["limit"],
            offset=query_params["offset"],
        )
        return Response(data=serializers.StructureLogsSLZ(logs).data)

    @swagger_auto_schema(
        query_serializer=serializers.PluginLogQueryParamsSLZ,
        request_body=serializers.PluginLogQueryBodySLZ,
        responses={200: serializers.IngressLogSLZ},
    )
    def query_ingress_logs(self, request, pd_id, plugin_id):
        """查询访问日志"""
        plugin = self.get_plugin_instance()

        slz = serializers.PluginLogQueryBodySLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slz = serializers.PluginLogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        logs = log_api.query_ingress_logs(
            pd=plugin.pd,
            instance=plugin,
            operator=request.user.username,
            time_range=query_params["smart_time_range"],
            query_string=data["query"]["query_string"],
            limit=query_params["limit"],
            offset=query_params["offset"],
        )
        return Response(data=serializers.IngressLogSLZ(logs).data)

    @swagger_auto_schema(
        query_serializer=serializers.PluginLogQueryParamsSLZ,
        request_body=serializers.PluginLogQueryBodySLZ,
        responses={200: serializers.DateHistogramSLZ},
    )
    def aggregate_date_histogram(
        self, request, pd_id, plugin_id, log_type: Literal["standard_output", "structure", "ingress"]
    ):
        """查询日志基于时间分布的直方图"""
        plugin = self.get_plugin_instance()

        slz = serializers.PluginLogQueryBodySLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slz = serializers.PluginLogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        date_histogram = log_api.aggregate_date_histogram(
            pd=plugin.pd,
            instance=plugin,
            log_type=log_type,
            operator=request.user.username,
            time_range=query_params["smart_time_range"],
            query_string=data["query"]["query_string"],
        )
        return Response(data=serializers.DateHistogramSLZ(date_histogram).data)

    @swagger_auto_schema(
        query_serializer=serializers.PluginLogQueryParamsSLZ,
        request_body=serializers.PluginLogQueryBodySLZ,
        responses={200: serializers.LogFieldFilterSLZ},
    )
    def aggregate_fields_filters(
        self, request, pd_id, plugin_id, log_type: Literal["standard_output", "structure", "ingress"]
    ):
        """查询日志基于时间分布的直方图"""
        plugin = self.get_plugin_instance()

        slz = serializers.PluginLogQueryBodySLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slz = serializers.PluginLogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        fields_filters = log_api.aggregate_fields_filters(
            pd=plugin.pd,
            instance=plugin,
            log_type=log_type,
            operator=request.user.username,
            time_range=query_params["smart_time_range"],
            query_string=data["query"]["query_string"],
            terms=data["query"]["terms"],
            exclude=data["query"]["exclude"],
        )
        return Response(data=serializers.LogFieldFilterSLZ(fields_filters, many=True).data)


class PluginConfigViewSet(PluginInstanceMixin, GenericViewSet):
    permission_classes = [
        IsAuthenticated,
        PluginCenterFeaturePermission,
        plugin_action_permission_class([Actions.MANAGE_CONFIGURATION]),
    ]
    pagination_class = None

    @swagger_auto_schema(responses={200: serializers.StubConfigSLZ(many=True)})
    def list(self, request, pd_id, plugin_id):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        plugin = self.get_plugin_instance(allow_archive=True)
        data = [{"__id__": config.unique_key, **config.row} for config in plugin.configs.all()]
        # 根据 key 按字母序排序
        data = sorted(data, key=lambda item: item['key'])
        return Response(data=serializers.make_config_slz_class(pd)(data, many=True).data)

    @swagger_auto_schema(request_body=serializers.StubConfigSLZ)
    def upsert(self, request, pd_id, plugin_id):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        plugin = self.get_plugin_instance()

        slz = serializers.make_config_slz_class(pd)(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        mgr = PluginConfigManager(pd=pd, plugin=plugin)
        mgr.save(data)
        # 同步配置
        sync_config(pd=pd, instance=plugin)

        # 操作记录: 修改配置信息
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.MODIFY,
            subject=constants.SubjectTypes.CONFIG_INFO,
        )
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, pd_id, plugin_id, config_id: str):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        plugin = self.get_plugin_instance()

        mgr = PluginConfigManager(pd=pd, plugin=plugin)
        mgr.delete(config_id)
        # 同步配置
        sync_config(pd=pd, instance=plugin)

        # 操作记录: 修改配置信息
        OperationRecord.objects.create(
            plugin=plugin,
            operator=request.user.pk,
            action=constants.ActionTypes.MODIFY,
            subject=constants.SubjectTypes.CONFIG_INFO,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
