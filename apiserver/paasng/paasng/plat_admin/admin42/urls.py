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
    bk_plugins,
    dashboard_templates,
    runtimes,
    smart_advisor,
)
from .views.engine import (
    certs,
    deployments,
    proc_spec,
)
from .views.operation import deploy

PART_MODULE = r"modules/(?P<module_name>[^/]+)"
PART_MODULE_WITH_ENV = "modules/(?P<module_name>[^/]+)/envs/(?P<environment>[^/]+)"

# admin42 主页路由
urlpatterns = [
    re_path(r"^$", views.FrontPageView.as_view(), name="admin.front_page"),
    # 配置管理
    ## 运行时管理
    ### BuildPack 管理
    re_path(
        r"^settings/runtimes/buildpack/manage/$",
        runtimes.BuildPackManageView.as_view(),
        name="admin.runtimes.buildpack.manage",
    ),
    ### BuildPack 管理 API
    re_path(
        r"^settings/runtimes/buildpack/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.buildpack",
    ),
    re_path(
        r"^settings/runtimes/buildpack/(?P<pk>[^/]+)/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.buildpack.detail",
    ),
    re_path(
        r"^settings/runtimes/buildpack/(?P<pk>[^/]+)/bind/$",
        runtimes.BuildPackAPIViewSet.as_view(dict(post="set_bound_builders", get="get_bound_builders")),
        name="admin.runtimes.buildpack.detail.bind",
    ),
    ### SlugBuilder 管理
    re_path(
        r"^settings/runtimes/slugbuilder/manage/$",
        runtimes.SlugBuilderManageView.as_view(),
        name="admin.runtimes.slugbuilder.manage",
    ),
    ### SlugBuilder 管理 API
    re_path(
        r"^settings/runtimes/slugbuilder/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.slugbuilder",
    ),
    re_path(
        r"^settings/runtimes/slugbuilder/(?P<pk>[^/]+)/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.slugbuilder.detail",
    ),
    re_path(
        r"^settings/runtime/slugbuilder/(?P<pk>[^/]+)/bind/$",
        runtimes.SlugBuilderAPIViewSet.as_view(dict(post="set_bound_buildpacks", get="get_bound_buildpacks")),
        name="admin.runtimes.slugbuilder.detail.bind",
    ),
    ### SlugRunner 管理
    re_path(
        r"^settings/runtimes/slugrunner/manage$",
        runtimes.AppSlugRunnerManageView.as_view(),
        name="admin.runtimes.slugrunner.manage",
    ),
    ### SlugRunner 管理 API
    re_path(
        r"^settings/runtimes/slugrunner/$",
        runtimes.SlugRunnerAPIViewSet.as_view(dict(post="create", get="list")),
        name="admin.runtimes.slugrunner",
    ),
    re_path(
        r"^settings/runtimes/slugrunner/(?P<pk>[^/]+)/$",
        runtimes.SlugRunnerAPIViewSet.as_view(dict(put="update", delete="destroy")),
        name="admin.runtimes.slugrunner.detail",
    ),
    ## 应用资源方案
    re_path(
        r"^settings/process_spec_plan/manage/$",
        proc_spec.ProcessSpecPlanManageView.as_view(),
        name="admin.process_spec_plan.manage",
    ),
    re_path(
        r"^settings/process_spec_plan/applications/$",
        proc_spec.ApplicationProcessSpecManageView.as_view(),
        name="admin.process_spec_plan.applications.manage",
    ),
    re_path(
        r"^settings/process_spec_plan/applications/(?P<app_code>[^/]+)/processes/$",
        proc_spec.ApplicationProcessSpecViewSet.as_view({"get": "list_processes"}),
        name="admin.process_spec_plan.applications.processes",
    ),
    ## 智能顾问
    ### 文档管理
    re_path(
        r"^settings/smart-advisor/documents/manage$",
        smart_advisor.DocumentaryLinkView.as_view(),
        name="admin.smart_advisor.documents.manage",
    ),
    re_path(
        r"^settings/smart-advisor/documents/$",
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.documents",
    ),
    re_path(
        r"^settings/smart-advisor/documents/(?P<pk>[^/]+)/$",
        smart_advisor.DocumentaryLinkManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.documents.detail",
    ),
    ### 失败提示管理
    re_path(
        r"^settings/smart-advisor/deploy_failure_tips/manage$",
        smart_advisor.DeployFailurePatternView.as_view(),
        name="admin.smart_advisor.deploy_failure_tips.manage",
    ),
    re_path(
        r"^settings/smart-advisor/deploy_failure_tips/$",
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.smart_advisor.deploy_failure_tips",
    ),
    re_path(
        r"^settings/smart-advisor/deploy_failure_tips/(?P<pk>[^/]+)/",
        smart_advisor.DeployFailurePatternManageViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.smart_advisor.deploy_failure_tips.detail",
    ),
    ## 共享证书管理
    re_path(
        r"^settings/certs/shared/manage/$",
        certs.SharedCertsManageView.as_view(),
        name="admin.shared.certs.manage",
    ),
    ## 仪表盘模板配置
    re_path(
        r"^settings/dashboard_template/manage/$",
        dashboard_templates.DashboardTemplateManageView.as_view(),
        name="admin.settings.dashboard_tmpl.manage",
    ),
    re_path(
        r"^settings/dashboard_template/$",
        dashboard_templates.DashboardTemplateViewSet.as_view(dict(post="create", get="list")),
        name="admin.settings.dashboard_tmpl",
    ),
    re_path(
        r"^settings/dashboard_template/(?P<pk>[^/]+)/",
        dashboard_templates.DashboardTemplateViewSet.as_view(dict(delete="destroy", put="update")),
        name="admin.settings.dashboard_tmpl.detail",
    ),
    ## 插件管理
    ### 插件分类配置
    re_path(
        r"^settings/bk_plugins/tags/manage/$",
        bk_plugins.BKPluginTagManageView.as_view(),
        name="admin.settings.bk_plugins.tags.manage",
    ),
    re_path(
        r"^settings/bk_plugins/tags/$",
        bk_plugins.BKPluginTagView.as_view(dict(post="create", get="list")),
        name="admin.settings.bk_plugins.tags",
    ),
    re_path(
        r"^settings/bk_plugins/tags/(?P<pk>[^/]+)/",
        bk_plugins.BKPluginTagView.as_view(dict(delete="destroy", put="update")),
        name="admin.settings.bk_plugins.tags.detail",
    ),
    ### 插件使用方配置
    re_path(
        r"^settings/bk_plugins/distributors/manage/$",
        bk_plugins.BKPluginDistributorsManageView.as_view(),
        name="admin.settings.bk_plugins.distributors.manage",
    ),
    re_path(
        r"^settings/bk_plugins/distributors/$",
        bk_plugins.BKPluginDistributorsView.as_view(dict(post="create", get="list")),
        name="admin.settings.bk_plugins.distributors",
    ),
    re_path(
        r"^settings/bk_plugins/distributors/(?P<pk>[^/]+)/",
        bk_plugins.BKPluginDistributorsView.as_view(dict(delete="destroy", put="update")),
        name="admin.settings.bk_plugins.distributors.detail",
    ),
    # 运营管理
    ## 应用运营评估
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
    ## 部署概览
    re_path(
        r"^deployments/$",
        deployments.DeploymentListView.as_view(),
        name="admin.deployments.list",
    ),
    ## 应用统计
    ### 应用部署统计
    re_path(
        r"^deployments/$",
        deployments.DeploymentListView.as_view(),
        name="admin.deployments.list",
    ),
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
    ### 开发者部署统计
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
    # 用户管理
    ## 用户列表
    re_path(
        r"^accountmgr/userprofiles/$",
        accountmgr.UserProfilesManageView.as_view(),
        name="admin.accountmgr.userprofiles.index",
    ),
    re_path(
        r"^api/accountmgr/userprofiles/$",
        accountmgr.UserProfilesManageViewSet.as_view({"post": "bulk_create", "put": "update", "delete": "destroy"}),
        name="admin.accountmgr.userprofile.api",
    ),
    # 添加 admin42 404 页面路由
    re_path(r"^.*$", views.Admin404View.as_view(), name="admin.404"),
]
