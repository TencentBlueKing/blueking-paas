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
from __future__ import absolute_import

from django.conf.urls import url

from . import runtime_views, views
from .views import accountmgr, applications, bk_plugins, runtimes, services, smart_advisor, sourcectl, templates
from .views.engine import (
    certs,
    clusters,
    config_vars,
    custom_domain,
    deployments,
    egress,
    operator,
    package,
    proc_spec,
    runtime,
)
from .views.operation import deploy

PART_MODULE = r'modules/(?P<module_name>[^/]+)'
PART_MODULE_WITH_ENV = 'modules/(?P<module_name>[^/]+)/envs/(?P<environment>[^/]+)'


urlpatterns = [
    url(r'^$', views.FrontPageView.as_view(), name='admin.front_page'),
    url(r'^slugbuilder/$', runtime_views.SlugBuilderListView.as_view(), name='admin.slugbuilder.list'),
    url(r'^slugbuilder/create$', runtime_views.SlugBuilderCreateView.as_view(), name='admin.slugbuilder.create'),
    url(r'^slugbuilder/update', runtime_views.SlugBuilderUpdateView.as_view(), name='admin.slugbuilder.update'),
    url(r'^slugbuilder/delete', runtime_views.SlugBuilderDeleteView.as_view(), name='admin.slugbuilder.delete'),
    url(r'^slugrunner/$', runtime_views.SlugRunnerListView.as_view(), name='admin.slugrunner.list'),
    url(r'^slugrunner/create$', runtime_views.SlugRunnerCreateView.as_view(), name='admin.slugrunner.create'),
    url(r'^slugrunner/update', runtime_views.SlugRunnerUpdateView.as_view(), name='admin.slugrunner.update'),
    url(r'^slugrunner/delete', runtime_views.SlugRunnerDeleteView.as_view(), name='admin.slugrunner.delete'),
    url(r'^buildpack/$', runtime_views.BuildPackListView.as_view(), name='admin.buildpack.list'),
    url(r'^buildpack/create$', runtime_views.BuildPackCreateView.as_view(), name='admin.buildpack.create'),
    url(r'^buildpack/update', runtime_views.BuildPackUpdateView.as_view(), name='admin.buildpack.update'),
    url(r'^buildpack/delete', runtime_views.BuildPackDeleteView.as_view(), name='admin.buildpack.delete'),
    # 平台管理
    url(r'^platform/$', applications.ApplicationListView.as_view(), name="admin.platform.index"),
    # 平台管理-应用资源方案
    url(
        r'^platform/process_spec_plan/manage/$',
        proc_spec.ProcessSpecPlanManageView.as_view(),
        name="admin.process_spec_plan.manage",
    ),
    # 平台管理-增强服务管理-服务管理页
    url(r'^platform/services/manage$', services.PlatformServicesView.as_view(), name='admin.services.manage'),
    # 平台管理-增强服务管理-服务管理API
    url(
        r'^platform/services/$',
        services.PlatformServicesManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.services",
    ),
    url(
        r'^platform/services/(?P<pk>[^/]+)/$',
        services.PlatformServicesManageViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.services.detail",
    ),
    # 平台管理-增强服务管理-方案管理页
    url(r'^platform/plans/manage$', services.PlatformPlanView.as_view(), name='admin.plans.manage'),
    # 平台管理-增强服务管理-方案管理API
    url(
        r'^platform/plans/$',
        services.PlatformPlanManageViewSet.as_view(dict(get="list")),
        name="admin.plans.list",
    ),
    url(
        r'^platform/services/(?P<service_id>[^/]+)/plans/$',
        services.PlatformPlanManageViewSet.as_view(dict(post="create")),
        name="admin.plans.create",
    ),
    url(
        r'^platform/services/(?P<service_id>[^/]+)/plans/(?P<plan_id>[^/]+)/$',
        services.PlatformPlanManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.plans.detail",
    ),
    # 平台管理-增强服务管理-资源池管理
    url(
        r'^platform/pre-created-instances/manage$',
        services.PreCreatedInstanceView.as_view(),
        name='admin.pre_created_instances.manage',
    ),
    url(
        r'^platform/pre-created-instances/$',
        services.PreCreatedInstanceManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.pre_created_instances",
    ),
    url(
        r'^platform/pre-created-instances/(?P<plan_id>[^/]+)/(?P<uuid>[^/]+)/$',
        services.PreCreatedInstanceManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.pre_created_instances.detail",
    ),
    # 平台管理-智能顾问-文档链接管理
    url(
        r'platform/smart-advisor/documents/manage$',
        smart_advisor.DocumentaryLinkView.as_view(),
        name="admin.smart_advisor.documents.manage",
    ),
    url(
        r'platform/smart-advisor/documents/$',
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.documents",
    ),
    url(
        r'platform/smart-advisor/documents/(?P<pk>[^/]+)/',
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.documents.detail",
    ),
    # 平台管理-智能顾问-失败提示管理
    url(
        r'platform/smart-advisor/deploy_failure_tips/manage$',
        smart_advisor.DeployFailurePatternView.as_view(),
        name="admin.smart_advisor.deploy_failure_tips.manage",
    ),
    url(
        r'platform/smart-advisor/deploy_failure_tips/$',
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.deploy_failure_tips",
    ),
    url(
        r'platform/smart-advisor/deploy_failure_tips/(?P<pk>[^/]+)/',
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.deploy_failure_tips.detail",
    ),
    # 平台管理-运行时管理-BuildPack管理
    url(
        r'^platform/runtime/buildpack/manage$',
        runtimes.BuildPackTemplateView.as_view(),
        name='admin.runtime.buildpack.manage',
    ),
    # 平台管理-运行时管理-BuildPack管理 API
    url(
        r'^platform/runtime/buildpack/$',
        runtimes.BuildPackAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtime.buildpack",
    ),
    url(
        r'^platform/runtime/buildpack/(?P<pk>[^/]+)/$',
        runtimes.BuildPackAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtime.buildpack.detail",
    ),
    # 平台管理-运行时管理-SlugBuilder管理
    url(
        r'^platform/runtime/slugbuilder/manage$',
        runtimes.SlugBuilderTemplateView.as_view(),
        name='admin.runtime.slugbuilder.manage',
    ),
    # 平台管理-运行时管理-SlugBuilder管理 API
    url(
        r'^platform/runtime/slugbuilder/$',
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtime.slugbuilder",
    ),
    url(
        r'^platform/runtime/slugbuilder/(?P<pk>[^/]+)/$',
        runtimes.SlugBuilderAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtime.slugbuilder.detail",
    ),
    url(
        r'^platform/runtime/slugbuilder/(?P<pk>[^/]+)/buildpacks',
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="set_buildpacks")),
        name="admin.runtime.slugbuilder.detail.bind",
    ),
    # 平台管理-运行时管理-SlugRunner管理
    url(
        r'^platform/runtime/slugrunner/manage$',
        runtimes.SlugRunnerTemplateView.as_view(),
        name='admin.runtime.slugrunner.manage',
    ),
    # 平台管理-运行时管理-BuildPack管理 API
    url(
        r'^platform/runtime/slugrunner/$',
        runtimes.SlugRunnerAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtime.slugrunner",
    ),
    url(
        r'^platform/runtime/slugrunner/(?P<pk>[^/]+)/$',
        runtimes.SlugRunnerAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtime.slugrunner.detail",
    ),
    # 平台管理-集群管理页
    url(r'^platform/clusters/manage/$', clusters.ClusterManageView.as_view(), name="admin.clusters.manage"),
    # 平台管理-集群组件管理页
    url(
        r'^platform/clusters/components/manage/$',
        clusters.ClusterComponentManageView.as_view(),
        name="admin.cluster_components.manage",
    ),
    # 平台管理-集群 Operator 管理页
    url(r'^platform/operators/manage/$', operator.OperatorManageView.as_view(), name="admin.operators.manage"),
    # 平台管理-共享证书管理
    url(r'^platform/certs/shared/manage/$', certs.SharedCertsManageView.as_view(), name="admin.shared.certs.manage"),
    # 平台管理-代码库配置
    url(
        r'platform/sourcectl/source_type_spec/manage/$',
        sourcectl.SourceTypeSpecManageView.as_view(),
        name="admin.sourcectl.source_type_spec.manage",
    ),
    url(
        r'platform/sourcectl/source_type_spec/$',
        sourcectl.SourceTypeSpecViewSet.as_view(dict(post="create", get="list")),
        name="admin.sourcectl.source_type_spec",
    ),
    url(
        r'platform/sourcectl/source_type_spec/(?P<pk>[^/]+)/',
        sourcectl.SourceTypeSpecViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.sourcectl.source_type_spec.detail",
    ),
    # 平台管理-应用列表页
    url(r'^applications/$', applications.ApplicationListView.as_view(), name="admin.applications.list"),
    # 应用详情-概览页
    url(
        r'^applications/(?P<code>[^/]+)/overview/$',
        applications.ApplicationOverviewView.as_view(),
        name="admin.applications.detail.overview",
    ),
    # 应用详情-环境配置管理
    url(
        f'^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/bind_cluster/$',
        applications.AppEnvConfManageView.as_view({'post': 'bind_cluster'}),
        name="admin.applications.engine.env_conf.bind_cluster",
    ),
    # 应用详情-进程管理
    url(
        r'^applications/(?P<code>[^/]+)/engine/process_specs/$',
        proc_spec.ProcessSpecManageView.as_view(),
        name="admin.applications.engine.process_specs",
    ),
    # 应用详情-包版本管理
    url(
        r'^applications/(?P<code>[^/]+)/engine/source_packages/manage/$',
        package.SourcePackageManageView.as_view(),
        name="admin.applications.engine.source_packages.manage",
    ),
    # 应用详情-包版本管理 API
    url(
        '^applications/(?P<code>[^/]+)/engine/source_packages/$',
        package.SourcePackageManageViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.source_packages.list",
    ),
    url(
        f'^applications/(?P<code>[^/]+)/{PART_MODULE}/engine/source_packages/(?P<pk>[^/]+)/$',
        package.SourcePackageManageViewSet.as_view(dict(get="download")),
        name="admin.applications.engine.source_packages.detail",
    ),
    # 应用详情 - Egress 管理
    url(
        r'^applications/(?P<code>[^/]+)/engine/egress/manage/$',
        egress.EgressManageView.as_view(),
        name="admin.applications.engine.egress.manage",
    ),
    # 应用详情 - Egress 管理 API
    url(
        f'^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/egress/$',
        egress.EgressManageViewSet.as_view(dict(get="get", post="create", delete="destroy")),
        name="admin.applications.engine.egress.detail",
    ),
    url(
        f'^applications/(?P<code>[^/]+)/{PART_MODULE_WITH_ENV}/engine/egress/ips/$',
        egress.EgressManageViewSet.as_view(dict(get="get_egress_ips")),
        name="admin.applications.engine.egress.ips",
    ),
    # 应用详情-环境变量管理
    url(
        r'^applications/(?P<code>[^/]+)/engine/config_vars/manage/$',
        config_vars.ConfigVarManageView.as_view(),
        name="admin.applications.engine.config_vars.manage",
    ),
    # 应用详情-环境变量管理 API
    url(
        '^application/(?P<code>[^/]+)/engine/config_vars$',
        config_vars.ConfigVarViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.config_vars.list",
    ),
    url(
        f'^application/(?P<code>[^/]+)/{PART_MODULE}/engine/config_vars$',
        config_vars.ConfigVarViewSet.as_view(dict(post="create")),
        name="admin.applications.engine.config_vars.create",
    ),
    url(
        f'^application/(?P<code>[^/]+)/{PART_MODULE}/engine/config_vars/(?P<id>[^/]+)/$',
        config_vars.ConfigVarViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.applications.engine.config_vars.detail",
    ),
    # 应用详情-运行时管理
    url(
        r'^applications/(?P<code>[^/]+)/engine/runtime/manage/$',
        runtime.RuntimeManageView.as_view(),
        name="admin.applications.engine.runtime.manage",
    ),
    # 应用详情-运行时管理 API
    url(
        '^applications/(?P<code>[^/]+)/engine/runtime/$',
        runtime.RuntimeManageViewSet.as_view(dict(get="list")),
        name="admin.applications.engine.runtime.list",
    ),
    url(
        f'^applications/(?P<code>[^/]+)/{PART_MODULE}/engine/runtime$',
        runtime.RuntimeManageViewSet.as_view(dict(post="bind")),
        name="admin.applications.engine.runtime.bind",
    ),
    # 应用详情-增强服务
    url(
        r'^applications/(?P<code>[^/]+)/services/$',
        services.ApplicationServicesView.as_view(),
        name="admin.applications.services",
    ),
    # 应用详情-增强服务 API
    url(
        r'api/applications/(?P<code>[^/]+)/services/$',
        services.ApplicationServicesManageViewSet.as_view({'get': 'list'}),
        name='admin.applications.services.list',
    ),
    url(
        r'api/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/env/(?P<environment>[^/]+)/services/'
        r'(?P<service_id>[^/]+)/provision/$',
        services.ApplicationServicesManageViewSet.as_view({'post': 'provision_instance'}),
        name='admin.applications.services.provision',
    ),
    url(
        r'api/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/services/'
        r'(?P<service_id>[^/]+)/instances/(?P<instance_id>[^/]+)/$',
        services.ApplicationServicesManageViewSet.as_view({'delete': 'recycle_resource'}),
        name='admin.applications.services.recycle_resource',
    ),
    # 应用详情-成员管理
    url(
        r'^applications/(?P<code>[^/]+)/base_info/memberships/$',
        applications.ApplicationMembersManageView.as_view(),
        name="admin.applications.detail.base_info.members",
    ),
    # 应用详情-成员管理 API
    url(
        r'^api/applications/(?P<code>[^/]+)/base_info/memberships/$',
        applications.ApplicationMembersManageViewSet.as_view({'get': 'list', 'post': 'update', 'delete': 'destroy'}),
        name='admin.applications.detail.base_info.members.api',
    ),
    # 应用详情-特性管理
    url(
        r'^applications/(?P<code>[^/]+)/base_info/feature_flags/$',
        applications.ApplicationFeatureFlagsView.as_view(),
        name="admin.applications.detail.base_info.feature_flags",
    ),
    # 应用详情-特性管理 API
    url(
        r'^api/applications/(?P<code>[^/]+)/base_info/feature_flags/$',
        applications.ApplicationFeatureFlagsViewset.as_view({'get': 'list', 'post': 'update'}),
        name="admin.applications.detail.base_info.feature_flags.api",
    ),
    # 应用详情-独立域名
    url(
        r'^applications/(?P<code>[^/]+)/engine/custom_domain/$',
        custom_domain.CustomDomainManageView.as_view(),
        name="admin.applications.engine.custom_domain",
    ),
    # 用户管理-首页
    url(r'^accountmgr/$', accountmgr.UserProfilesManageView.as_view(), name="admin.accountmgr.index"),
    # 用户管理-用户列表
    url(
        r'^accountmgr/userprofiles/$',
        accountmgr.UserProfilesManageView.as_view(),
        name="admin.accountmgr.userprofiles.index",
    ),
    # 用户管理-用户列表 API
    url(
        r'^api/accountmgr/userprofiles/$',
        accountmgr.UserProfilesManageViewSet.as_view(
            {'get': 'list', 'post': 'bulk_create', "put": "update", "delete": "destroy"}
        ),
        name="admin.accountmgr.userprofile.api",
    ),
    # 用户管理-用户特性管理
    url(
        r'^accountmgr/account_feature_flags/$',
        accountmgr.AccountFeatureFlagManageView.as_view(),
        name="admin.accountmgr.account_feature_flags.index",
    ),
    # 用户管理-用户特性管理 API
    url(
        r'^api/accountmgr/account_feature_flags/$',
        accountmgr.AccountFeatureFlagManageViewSet.as_view({'get': 'list', 'post': 'update_or_create'}),
        name="admin.accountmgr.account_feature_flags.api",
    ),
    # 部署列表页
    url(r'^deployments/$', deployments.DeploymentListView.as_view(), name="admin.deployments.list"),
    url(
        r'^operation/statistics/deploy/apps/$',
        deploy.AppDeployStatisticsView.as_view({'get': 'get', 'post': 'export'}),
        name="admin.operation.statistics.deploy.apps",
    ),
    url(
        r'^operation/statistics/deploy/apps/export/$',
        deploy.AppDeployStatisticsView.as_view({'get': 'export'}),
        name="admin.operation.statistics.deploy.apps.export",
    ),
    url(
        r'^operation/statistics/deploy/developers/$',
        deploy.DevelopersDeployStatisticsView.as_view({'get': 'get'}),
        name="admin.operation.statistics.deploy.developers",
    ),
    url(
        r'^operation/statistics/deploy/developers/export/$',
        deploy.DevelopersDeployStatisticsView.as_view({'get': 'export'}),
        name="admin.operation.statistics.deploy.developers.export",
    ),
]

# 应用配置管理，可以提供给管理应用、插件模板的同学使用
urlpatterns += [
    # 平台管理-模板配置
    url(
        r'configuration/tmpls/manage/$',
        templates.TemplateManageView.as_view(),
        name="admin.configuration.tmpl.manage",
    ),
    url(
        r'configuration/tmpls/$',
        templates.TemplateViewSet.as_view(dict(post="create", get="list")),
        name="admin.configuration.tmpl",
    ),
    url(
        r'configuration/tmpls/(?P<pk>[^/]+)/',
        templates.TemplateViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.tmpl.detail",
    ),
    # 平台管理-插件分类配置
    url(
        r'configuration/bk_plugins/tags/manage/$',
        bk_plugins.BKPluginTagManageView.as_view(),
        name="admin.configuration.bk_plugins.tags.manage",
    ),
    url(
        r'configuration/bk_plugins/tags/$',
        bk_plugins.BKPluginTagView.as_view(dict(post="create", get="list")),
        name="admin.configuration.bk_plugins.tags",
    ),
    url(
        r'configuration/bk_plugins/tags/(?P<pk>[^/]+)/',
        bk_plugins.BKPluginTagView.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.bk_plugins.tags.detail",
    ),
    # 平台管理-插件使用方配置
    url(
        r'configuration/bk_plugins/distributors/manage/$',
        bk_plugins.BKPluginDistributorsManageView.as_view(),
        name="admin.configuration.bk_plugins.distributors.manage",
    ),
    url(
        r'configuration/bk_plugins/distributors/$',
        bk_plugins.BKPluginDistributorsView.as_view(dict(post="create", get="list")),
        name="admin.configuration.bk_plugins.distributors",
    ),
    url(
        r'configuration/bk_plugins/distributors/(?P<pk>[^/]+)/',
        bk_plugins.BKPluginDistributorsView.as_view(dict(delete="destroy", put="update")),
        name="admin.configuration.bk_plugins.distributors.detail",
    ),
]
