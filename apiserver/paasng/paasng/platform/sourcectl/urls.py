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

from paasng.utils.basic import make_app_pattern, re_path

from . import views

urlpatterns = [
    # 用户svn账户 相关
    re_path(
        r"^api/sourcectl/bksvn/accounts/$",
        views.SvnAccountViewSet.as_view({"get": "list", "post": "create"}),
        name="api.sourcectl.bksvn.accounts",
    ),
    re_path(
        r"^api/sourcectl/bksvn/accounts/(?P<id>\d+)/reset/$",
        views.SvnAccountViewSet.as_view({"put": "update"}),
        name="api.sourcectl.bksvn.accounts.reset",
    ),
    re_path(
        r"^api/sourcectl/(?P<source_control_type>.+)/repos/", views.GitRepoViewSet.as_view({"get": "get_repo_list"})
    ),
    re_path(
        r"^api/sourcectl/(?P<source_control_type>.+)/groups/", views.GitRepoViewSet.as_view({"get": "get_group_list"})
    ),
    # 获取用户可用源码仓库
    re_path(
        r"^api/sourcectl/providers/$",
        views.AccountAllowAppSourceControlView.as_view(),
        name="api.sourcectl.providers.list",
    ),
    # 获取当前模块可用源码仓库系统
    re_path(
        make_app_pattern(r"/providers/$", include_envs=False, prefix="api/sourcectl/applications/"),
        views.ModuleSourceProvidersViewSet.as_view({"get": "list"}),
        name="api.sourcectl.module_providers.list",
    ),
    # 重新下载默认模块初始化模版代码
    re_path(
        r"^api/sourcectl/init_templates/(?P<code>[^/]+)/$",
        views.ModuleInitTemplateViewSet.as_view({"post": "download_default"}),
        name="api.sourcectl.template.generator",
    ),
    re_path(
        make_app_pattern(r"/sourcectl/init_template/$", include_envs=False),
        views.ModuleInitTemplateViewSet.as_view({"post": "download"}),
        name="api.sourcectl.init_template",
    ),
    # 用户修改仓库类型, (是否需要将 module_name 添加到 url 路径上?
    re_path(
        make_app_pattern(r"/sourcectl/repo/modify/$", include_envs=False),
        views.RepoBackendControlViewSet.as_view({"post": "modify"}),
        name="api.sourcectl.repo.modify",
    ),
    # 源码包管理
    re_path(
        make_app_pattern(r"/source_package/link/$", include_envs=False),
        views.ModuleSourcePackageViewSet.as_view({"post": "upload_via_url"}),
        name="api.sourcectl.source_package.create_via_url",
    ),
    re_path(
        make_app_pattern(r"/source_package/$", include_envs=False),
        views.ModuleSourcePackageViewSet.as_view({"get": "list"}),
        name="api.sourcectl.source_package",
    ),
]


# 与部署相关的接口
urlpatterns += [
    re_path(
        make_app_pattern("/repo/branches/$", include_envs=False),
        views.RepoDataViewSet.as_view({"get": "get_repo_branches"}),
        name="api.repo.branches",
    ),
    re_path(
        make_app_pattern("/repo/tags/$", include_envs=False),
        views.SVNRepoTagsView.as_view(),
        name="api.applications.repo.tags",
    ),
    re_path(
        make_app_pattern("/repo/revisions/(?P<smart_revision>.*)$", include_envs=False),
        views.RevisionInspectViewSet.as_view({"get": "retrieve"}),
        name="api.repo.revisions.detail",
    ),
    re_path(
        make_app_pattern(
            r"/repo/commit-diff/(?P<from_revision>[\w:]+)/(?P<to_revision>[\w:]+)/logs/$", include_envs=False
        ),
        views.RepoDataViewSet.as_view({"get": "get_diff_commit_logs"}),
        name="api.repo.revision.comment-diff",
    ),
    re_path(
        make_app_pattern(
            r"/repo/commit-diff-external/(?P<from_revision>[\w:]+)/(?P<to_revision>.*)/$", include_envs=False
        ),
        views.RepoDataViewSet.as_view({"get": "get_compare_url"}),
        name="api.repo.revision.comment-diff-external",
    ),
]
