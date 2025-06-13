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

from __future__ import absolute_import

from paasng.utils.basic import re_path

from . import views
from .views import (
    accountmgr,
    applications,
    audit,
    bk_plugins,
    dashboard_templates,
    runtimes,
    services,
    smart_advisor,
    sourcectl,
    templates,
)
from .views.engine import (
    certs,
    config_vars,
    custom_domain,
    deployments,
    egress,
    log_config,
    package,
    proc_spec,
    runtime,
)
from .views.operation import deploy

PART_MODULE = r"modules/(?P<module_name>[^/]+)"
PART_MODULE_WITH_ENV = "modules/(?P<module_name>[^/]+)/envs/(?P<environment>[^/]+)"


urlpatterns = [
    re_path(r"^$", views.FrontPageView.as_view(), name="admin.front_page"),
    # 平台管理
    re_path(r"^platform/$", applications.ApplicationListView.as_view(), name="admin.platform.index"),
    # 平台管理-应用资源方案
    re_path(
        r"^platform/process_spec_plan/manage/$",
        proc_spec.ProcessSpecPlanManageView.as_view(),
        name="admin.process_spec_plan.manage",
    ),
    re_path(
        r"^platform/process_spec_plan/applications/$",
        proc_spec.ApplicationProcessSpecManageView.as_view(),
        name="admin.process_spec_plan.applications.manage",
    ),
    re_path(
        r"^platform/process_spec_plan/applications/(?P<app_code>[^/]+)/processes/$",
        proc_spec.ApplicationProcessSpecViewSet.as_view({"get": "list_processes"}),
        name="admin.process_spec_plan.applications.processes",
    ),
    # 平台管理-智能顾问-文档链接管理
    re_path(
        r"^platform/smart-advisor/documents/manage$",
        smart_advisor.DocumentaryLinkView.as_view(),
        name="admin.smart_advisor.documents.manage",
    ),
    re_path(
        r"^platform/smart-advisor/documents/$",
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.documents",
    ),
    re_path(
        r"^platform/smart-advisor/documents/(?P<pk>[^/]+)/$",
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.documents.detail",
    ),
    # 平台管理-智能顾问-失败提示管理
    re_path(
        r"^platform/smart-advisor/deploy_failure_tips/manage$",
        smart_advisor.DeployFailurePatternView.as_view(),
        name="admin.smart_advisor.deploy_failure_tips.manage",
    ),
    re_path(
        r"^platform/smart-advisor/deploy_failure_tips/$",
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.deploy_failure_tips",
    ),
    re_path(
        r"^platform/smart-advisor/deploy_failure_tips/(?P<pk>[^/]+)/",
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.deploy_failure_tips.detail",
    ),
    # 平台管理-运行时管理-BuildPack 管理
    re_path(
        r"^platform/runtimes/buildpack/manage/$",
        runtimes.BuildPackManageView.as_view(),
        name="admin.runtimes.buildpack.manage",
    ),
    # 平台管理-运行时管理-BuildPack 管理 API
    re_path(
        "^platform/runtimes/buildpack/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.buildpack",
    ),
    re_path(
        r"^platform/runtimes/buildpack/(?P<pk>[^/]+)/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.buildpack.detail",
    ),
    re_path(
        r"^platform/runtimes/buildpack/(?P<pk>[^/]+)/bind/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(post="set_bound_builders", get="get_bound_builders")),
        name="admin.runtimes.buildpack.detail.bind",
    ),
    # 平台管理-运行时管理-SlugBuilder 管理
    re_path(
        r"^platform/runtimes/slugbuilder/manage/$",
        runtimes.SlugBuilderManageView.as_view(),
        name="admin.runtimes.slugbuilder.manage",
    ),
    # 平台管理-运行时管理-SlugBuilder 管理 API
    re_path(
        r"^platform/runtimes/slugbuilder/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.slugbuilder",
    ),
    re_path(
        r"^platform/runtimes/slugbuilder/(?P<pk>[^/]+)/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.slugbuilder.detail",
    ),
    re_path(
        r"^platform/runtime/slugbuilder/(?P<pk>[^/]+)/bind/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="set_bound_buildpacks", get="get_bound_buildpacks")),
        name="admin.runtimes.slugbuilder.detail.bind",
    ),
    # 平台管理-运行时管理-SlugRunner 管理
    re_path(
        r"^platform/runtimes/slugrunner/manage$",
        runtimes.AppSlugRunnerManageView.as_view(),
        name="admin.runtimes.slugrunner.manage",
    ),
    # 平台管理-运行时管理-SlugRunner 管理 API
    re_path(
        r"^platform/runtimes/slugrunner/$",
        runtimes.SlugRunnerAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.slugrunner",
    ),
    re_path(
        r"^platform/runtimes/slugrunner/(?P<pk>[^/]+)/$",
        runtimes.SlugRunnerAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.slugrunner.detail",
    ),
    # 平台管理-共享证书管理
    re_path(
        r"^platform/certs/shared/manage/$", certs.SharedCertsManageView.as_view(), name="admin.shared.certs.manage"
    ),
    # 平台管理-代码库配置
    re_path(
        r"^platform/sourcectl/source_type_spec/manage/$",
        sourcectl.SourceTypeSpecManageView.as_view(),
        name="admin.sourcectl.source_type_spec.manage",
    ),
    re_path(
        r"^platform/sourcectl/source_type_spec/$",
        sourcectl.SourceTypeSpecViewSet.as_view(dict(post="create", get="list")),
        name="admin.sourcectl.source_type_spec",
    ),
    re_path(
        r"^platform/sourcectl/source_type_spec/(?P<pk>[^/]+)/",
        sourcectl.SourceTypeSpecViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.sourcectl.source_type_spec.detail",
    ),
    # 平台管理-应用列表页
    re_path(r"^applications/$", applications.ApplicationListView.as_view(), name="admin.applications.list"),
    # 平台管理-应用运营评估
    re_path(
        r"^applications/evaluations/$",
        applications.ApplicationOperationEvaluationView.as_view(),
        name="admin.applications.operation_evaluation.list",
    ),
    re_path(
        r"^applications/evaluations/export/$",
        applications.ApplicationOperationReportExportView.as_view({"get": "export"}),
        name="admin.applications.operation_evaluation.export",
    ),
    # 应用详情-概览页
    re_path(
        r"^applications/(?P<code>[^/]+)/overview/$",
        applications.ApplicationOverviewView.as_view(),
        name="admin.applications.detail.overview",
    ),
    # 应用详情-环境配置管理
    re_path(
        f"^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/bind_cluster/$",
        applications.AppEnvConfManageView.as_view({"post": "bind_cluster"}),
        name="admin.applications.engine.env_conf.bind_cluster",
    ),
    # 应用详情-进程管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/process_specs/$",
        proc_spec.ProcessSpecManageView.as_view(),
        name="admin.applications.engine.process_specs",
    ),
    # 应用详情-包版本管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/source_packages/manage/$",
        package.SourcePackageManageView.as_view(),
        name="admin.applications.engine.source_packages.manage",
    ),
    # 应用详情-包版本管理 API
    re_path(
        "^applications/(?P<code>[^/]+)/engine/source_packages/$",
        package.SourcePackageManageViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.source_packages.list",
    ),
    re_path(
        f"^applications/(?P<code>[^/]+)/{PART_MODULE}/engine/source_packages/(?P<pk>[^/]+)/$",
        package.SourcePackageManageViewSet.as_view(dict(get="download")),
        name="admin.applications.engine.source_packages.detail",
    ),
    # 应用详情 - Egress 管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/egress/manage/$",
        egress.EgressManageView.as_view(),
        name="admin.applications.engine.egress.manage",
    ),
    # 应用详情 - Egress 管理 API
    re_path(
        f"^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/egress/$",
        egress.EgressManageViewSet.as_view(dict(get="get", post="create", delete="destroy")),
        name="admin.applications.engine.egress.detail",
    ),
    re_path(
        f"^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/egress/ips/$",
        egress.EgressManageViewSet.as_view(dict(get="get_egress_ips")),
        name="admin.applications.engine.egress.ips",
    ),
    # 应用详情-环境变量管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/config_vars/manage/$",
        config_vars.ConfigVarManageView.as_view(),
        name="admin.applications.engine.config_vars.manage",
    ),
    # 应用详情-环境变量管理 API
    re_path(
        r"^application/(?P<code>[^/]+)/engine/config_vars$",
        config_vars.ConfigVarViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.config_vars.list",
    ),
    re_path(
        f"^application/(?P<code>[^/]+)/{PART_MODULE}/engine/config_vars$",
        config_vars.ConfigVarViewSet.as_view(dict(post="create")),
        name="admin.applications.engine.config_vars.create",
    ),
    re_path(
        f"^application/(?P<code>[^/]+)/{PART_MODULE}/engine/config_vars/(?P<id>[^/]+)/$",
        config_vars.ConfigVarViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.applications.engine.config_vars.detail",
    ),
    # 应用详情-运行时管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/runtime/manage/$",
        runtime.RuntimeManageView.as_view(),
        name="admin.applications.engine.runtime.manage",
    ),
    # 应用详情-运行时管理 API
    re_path(
        "^applications/(?P<code>[^/]+)/engine/runtime/$",
        runtime.RuntimeManageViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.runtime.list",
    ),
    re_path(
        f"^applications/(?P<code>[^/]+)/{PART_MODULE}/engine/runtime$",
        runtime.RuntimeManageViewSet.as_view(dict(post="bind")),
        name="admin.applications.engine.runtime.bind",
    ),
    # 应用详情-增强服务
    re_path(
        r"^applications/(?P<code>[^/]+)/services/$",
        services.ApplicationServicesView.as_view(),
        name="admin.applications.services",
    ),
    # 应用详情-增强服务 API
    re_path(
        r"^api/applications/(?P<code>[^/]+)/services/$",
        services.ApplicationServicesManageViewSet.as_view({"get": "list"}),
        name="admin.applications.services.list",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/env/(?P<environment>[^/]+)/services/"
        r"(?P<service_id>[^/]+)/provision/$",
        services.ApplicationServicesManageViewSet.as_view({"post": "provision_instance"}),
        name="admin.applications.services.provision",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/services/"
        r"(?P<service_id>[^/]+)/instances/(?P<instance_id>[^/]+)/$",
        services.ApplicationServicesManageViewSet.as_view({"delete": "recycle_resource"}),
        name="admin.applications.services.recycle_resource",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/services/unbound/$",
        services.ApplicationUnboundServicesManageViewSet.as_view({"get": "list"}),
        name="admin.applications.services.unbound.list",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/services/"
        r"(?P<service_id>[^/]+)/unbound/instances/(?P<instance_id>[^/]+)/$",
        services.ApplicationUnboundServicesManageViewSet.as_view({"delete": "recycle_resource"}),
        name="admin.applications.services.unbound.recycle_resource",
    ),
    # 应用详情-成员管理
    re_path(
        r"^applications/(?P<code>[^/]+)/base_info/memberships/$",
        applications.ApplicationMembersManageView.as_view(),
        name="admin.applications.detail.base_info.members",
    ),
    # 应用详情-成员管理 API
    re_path(
        r"^api/applications/(?P<code>[^/]+)/base_info/memberships/$",
        applications.ApplicationMembersManageViewSet.as_view({"get": "list", "post": "update"}),
        name="admin.applications.detail.base_info.members.api",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/base_info/memberships/(?P<username>[^/]+)/$",
        applications.ApplicationMembersManageViewSet.as_view({"delete": "destroy"}),
        name="admin.applications.detail.base_info.members.api",
    ),
    re_path(
        r"^api/applications/(?P<code>[^/]+)/base_info/plugin/memberships/$",
        bk_plugins.BKPluginMembersManageViewSet.as_view({"post": "update"}),
        name="admin.applications.detail.base_info.plugin.members.api",
    ),
    # 应用详情-特性管理
    re_path(
        r"^applications/(?P<code>[^/]+)/base_info/feature_flags/$",
        applications.ApplicationFeatureFlagsView.as_view(),
        name="admin.applications.detail.base_info.feature_flags",
    ),
    # 应用详情-特性管理 API
    re_path(
        r"^api/applications/(?P<code>[^/]+)/base_info/feature_flags/$",
        applications.ApplicationFeatureFlagsViewset.as_view({"get": "list", "post": "update"}),
        name="admin.applications.detail.base_info.feature_flags.api",
    ),
    # 应用详情-独立域名
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/custom_domain/$",
        custom_domain.CustomDomainManageView.as_view(),
        name="admin.applications.engine.custom_domain",
    ),
    # 应用详情-日志采集管理
    re_path(
        r"^applications/(?P<code>[^/]+)/engine/log_config/$",
        log_config.LogConfigView.as_view(),
        name="admin.applications.engine.log_config.manage",
    ),
    # 用户管理-首页
    re_path(r"^accountmgr/$", accountmgr.UserProfilesManageView.as_view(), name="admin.accountmgr.index"),
    # 用户管理-用户列表
    re_path(
        r"^accountmgr/userprofiles/$",
        accountmgr.UserProfilesManageView.as_view(),
        name="admin.accountmgr.userprofiles.index",
    ),
    # 用户管理-用户列表 API
    re_path(
        r"^api/accountmgr/userprofiles/$",
        accountmgr.UserProfilesManageViewSet.as_view({"post": "bulk_create", "put": "update", "delete": "destroy"}),
        name="admin.accountmgr.userprofile.api",
    ),
    # 部署列表页
    re_path(r"^deployments/$", deployments.DeploymentListView.as_view(), name="admin.deployments.list"),
    re_path(
        r"^operation/statistics/deploy/apps/$",
        deploy.AppDeployStatisticsView.as_view({"get": "get", "post": "export"}),
        name="admin.operation.statistics.deploy.apps",
    ),
    re_path(
        r"^operation/statistics/deploy/apps/export/$",
        deploy.AppDeployStatisticsView.as_view({"get": "export"}),
        name="admin.operation.statistics.deploy.apps.export",
    ),
    re_path(
        r"^operation/statistics/deploy/developers/$",
        deploy.DevelopersDeployStatisticsView.as_view({"get": "get"}),
        name="admin.operation.statistics.deploy.developers",
    ),
    re_path(
        r"^operation/statistics/deploy/developers/export/$",
        deploy.DevelopersDeployStatisticsView.as_view({"get": "export"}),
        name="admin.operation.statistics.deploy.developers.export",
    ),
]

# 应用配置管理，可以提供给管理应用、插件模板的同学使用
urlpatterns += [
    # 应用配置管理-模板配置
    re_path(
        r"^configuration/tmpls/manage/$",
        templates.TemplateManageView.as_view(),
        name="admin.configuration.tmpl.manage",
    ),
    re_path(
        r"^configuration/tmpls/$",
        templates.TemplateViewSet.as_view(dict(post="create", get="list")),
        name="admin.configuration.tmpl",
    ),
    re_path(
        r"^configuration/tmpls/(?P<pk>[^/]+)/",
        templates.TemplateViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.tmpl.detail",
    ),
    # 应用配置管理-插件分类配置
    re_path(
        r"^configuration/bk_plugins/tags/manage/$",
        bk_plugins.BKPluginTagManageView.as_view(),
        name="admin.configuration.bk_plugins.tags.manage",
    ),
    re_path(
        r"^configuration/bk_plugins/tags/$",
        bk_plugins.BKPluginTagView.as_view(dict(post="create", get="list")),
        name="admin.configuration.bk_plugins.tags",
    ),
    re_path(
        r"^configuration/bk_plugins/tags/(?P<pk>[^/]+)/",
        bk_plugins.BKPluginTagView.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.bk_plugins.tags.detail",
    ),
    # 应用配置管理-插件使用方配置
    re_path(
        r"^configuration/bk_plugins/distributors/manage/$",
        bk_plugins.BKPluginDistributorsManageView.as_view(),
        name="admin.configuration.bk_plugins.distributors.manage",
    ),
    re_path(
        r"^configuration/bk_plugins/distributors/$",
        bk_plugins.BKPluginDistributorsView.as_view(dict(post="create", get="list")),
        name="admin.configuration.bk_plugins.distributors",
    ),
    re_path(
        r"^configuration/bk_plugins/distributors/(?P<pk>[^/]+)/",
        bk_plugins.BKPluginDistributorsView.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.bk_plugins.distributors.detail",
    ),
    # 应用配置管理-仪表盘模板配置
    re_path(
        r"^configuration/dashboard_template/manage/$",
        dashboard_templates.DashboardTemplateManageView.as_view(),
        name="admin.configuration.dashboard_tmpl.manage",
    ),
    re_path(
        r"^configuration/dashboard_template/$",
        dashboard_templates.DashboardTemplateViewSet.as_view(dict(post="create", get="list")),
        name="admin.configuration.dashboard_tmpl",
    ),
    re_path(
        r"^configuration/dashboard_template/(?P<pk>[^/]+)/",
        dashboard_templates.DashboardTemplateViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.dashboard_tmpl.detail",
    ),
]


# 操作审计
urlpatterns += [
    # 操作审计
    re_path(
        r"^audit/$",
        audit.AdminOperationAuditManageView.as_view(),
        name="admin.audit.index",
    ),
    re_path(
        r"^audit/application$",
        audit.AdminAppOperationAuditManageView.as_view(),
        name="admin.audit.app",
    ),
    # 操作审计相关 API
    re_path(
        r"^api/audit/operations/(?P<pk>[^/]+)/",
        audit.AdminOperationAuditViewSet.as_view(),
        name="admin.audit.detail",
    ),
    re_path(
        r"^api/audit/application/operations/(?P<pk>[^/]+)/",
        audit.AdminAppOperationAuditViewSet.as_view(),
        name="admin.audit.app.detail",
    ),
]
