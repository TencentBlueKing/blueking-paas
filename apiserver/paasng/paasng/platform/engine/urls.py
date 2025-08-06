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

from paasng.utils.basic import make_app_pattern, make_app_pattern_with_global_envs, re_path

from . import views

PVAR_UUID = "(?P<uuid>[0-9a-f-]{32,36})"

# Deployment
urlpatterns = [
    re_path(
        make_app_pattern(r"/released_info/$"),
        views.ReleasedInfoViewSet.as_view({"get": "get_current_info"}),
        name="api.released_info.get_current_info",
    ),
    re_path(
        make_app_pattern(r"/released_state/$"),
        views.ReleasedInfoViewSet.as_view({"get": "get_current_state"}),
        name="api.released_info.get_current_state",
    ),
    re_path(
        make_app_pattern_with_global_envs(r"/releases/$"),
        views.ReleasesViewset.as_view({"post": "release"}),
        name="api.releases.release",
    ),
    re_path(
        make_app_pattern(r"/config_vars/$", include_envs=False),
        views.ConfigVarViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="api.config_vars",
    ),
    re_path(
        make_app_pattern(r"/config_vars/(?P<id>\d+)/$", include_envs=False),
        views.ConfigVarViewSet.as_view(
            {
                "put": "update",
                "delete": "destroy",
            }
        ),
        name="api.config_vars.single",
    ),
    re_path(
        make_app_pattern(r"/config_vars/clone_from/(?P<source_module_name>[^/]+)$", include_envs=False),
        views.ConfigVarViewSet.as_view({"post": "clone"}),
        name="api.config_vars.clone",
    ),
    re_path(
        make_app_pattern(r"/config_vars/batch/$", include_envs=False),
        views.ConfigVarViewSet.as_view({"post": "batch"}),
        name="api.config_vars.batch",
    ),
    re_path(
        make_app_pattern(r"/config_vars/import/$", include_envs=False),
        views.ConfigVarImportExportViewSet.as_view(
            {
                "post": "import_by_file",
            }
        ),
        name="api.config_vars.import_by_file",
    ),
    re_path(
        make_app_pattern(r"/config_vars/export/$", include_envs=False),
        views.ConfigVarImportExportViewSet.as_view(
            {
                "get": "export_to_file",
            }
        ),
        name="api.config_vars.export_to_file",
    ),
    re_path(
        make_app_pattern(r"/config_vars/template/$", include_envs=False),
        views.ConfigVarImportExportViewSet.as_view(
            {
                "get": "template",
            }
        ),
        name="api.config_vars.template",
    ),
    re_path(
        make_app_pattern(r"/config_vars/preset/$", include_envs=False),
        views.PresetConfigVarViewSet.as_view({"get": "list"}),
        name="api.preset_config_vars",
    ),
    re_path(
        make_app_pattern(r"/config_vars/builtin/$", include_envs=False),
        views.ConfigVarBuiltinViewSet.as_view({"get": "list_builtin_envs"}),
        name="api.config_vars.builtin",
    ),
    re_path(
        make_app_pattern(r"/config_vars/conflict_info/$", include_envs=False),
        views.ConflictedConfigVarsViewSet.as_view({"get": "list_configvar_conflicted_keys"}),
        name="api.config_vars.conflict_info",
    ),
    re_path(
        make_app_pattern(r"/config_vars/(?P<config_vars_key>[A-Z][A-Z0-9_]*)/$", include_envs=False),
        views.ConfigVarViewSet.as_view(
            {
                "get": "retrieve_by_key",
                "post": "upsert_by_key",
            }
        ),
        name="api.config_vars_by_key",
    ),
    # deploy
    re_path(
        make_app_pattern(r"/deployments/%s/result/$" % PVAR_UUID, include_envs=False),
        views.DeploymentViewSet.as_view({"get": "get_deployment_result"}),
        name="api.deploy.result",
    ),
    re_path(
        make_app_pattern(r"/deployments/%s/logs/export/$" % PVAR_UUID, include_envs=False),
        views.DeploymentViewSet.as_view({"get": "export_deployment_log"}),
        name="api.deploy.export_log",
    ),
    re_path(
        make_app_pattern(r"/deployments/{}/interruptions/$".format(PVAR_UUID), include_envs=False),
        views.DeploymentViewSet.as_view({"post": "user_interrupt"}),
        name="api.deploy.release_interruptions",
    ),
    re_path(
        make_app_pattern(r"/deployments/lists/$", include_envs=False),
        views.DeploymentViewSet.as_view({"get": "list"}),
        name="api.deploy.lists",
    ),
    re_path(
        make_app_pattern(r"/deployments/$"), views.DeploymentViewSet.as_view({"post": "deploy"}), name="api.deploy"
    ),
    re_path(
        make_app_pattern(r"/deployments/resumable/$"),
        views.DeploymentViewSet.as_view({"get": "get_resumable_deployment"}),
        name="api.deploy.resumable",
    ),
    re_path(
        make_app_pattern(r"/deploy/preparations$"),
        views.DeploymentViewSet.as_view({"get": "check_preparations"}),
        name="api.deploy.check_preparations",
    ),
    re_path(make_app_pattern(r"/offlines/$"), views.OfflineViewset.as_view({"post": "offline"}), name="api.offline"),
    re_path(
        make_app_pattern(r"/offlines/resumable/$"),
        views.OfflineViewset.as_view({"get": "get_resumable_offline_operations"}),
        name="api.offline.resumable",
    ),
    re_path(
        make_app_pattern(r"/offlines/%s/result/$" % PVAR_UUID, include_envs=False),
        views.OfflineViewset.as_view({"get": "get_offline_result"}),
        name="api.deploy.result",
    ),
    re_path(
        make_app_pattern(r"/deploy_operations/lists/$", include_envs=False),
        views.OperationsViewset.as_view({"get": "list"}),
        name="api.deploy_operation.lists",
    ),
    # build artifact
    re_path(
        make_app_pattern(r"/build/artifact/image/$", include_envs=False),
        views.ImageArtifactViewSet.as_view({"get": "list_image"}),
        name="api.build.image.list",
    ),
    re_path(
        make_app_pattern(r"/build/artifact/image/(?P<build_id>[^/]+)$", include_envs=False),
        views.ImageArtifactViewSet.as_view({"get": "retrieve_image_detail"}),
        name="api.build.image.detail",
    ),
    # build process
    re_path(
        make_app_pattern(r"/build_process/$", include_envs=False),
        views.BuildProcessViewSet.as_view({"get": "list"}),
        name="api.build_process.list",
    ),
]


# Process Metrics Start

urlpatterns += [
    re_path(
        make_app_pattern(r"/metrics/$"),
        views.ProcessResourceMetricsViewset.as_view({"get": "list"}),
        name="api.process.metrics.get",
    ),
]

# Process Metrics End

# Deploy Phase Start

urlpatterns += [
    re_path(
        make_app_pattern(r"/deploy_phases/$"),
        views.DeployPhaseViewSet.as_view({"get": "get_frame"}),
        name="api.deploy.phase",
    ),
    re_path(
        make_app_pattern(r"/deploy_phases/%s/$" % PVAR_UUID),
        views.DeployPhaseViewSet.as_view({"get": "get_result"}),
        name="api.deploy.phase.result",
    ),
]

# Deploy Phase End
