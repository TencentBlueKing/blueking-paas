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

from paasng.plat_mgt.applications import views
from paasng.plat_mgt.bk_plugins.views import BKPluginMembersManageViewSet
from paasng.utils.basic import make_app_pattern, re_path

SERVICE_UUID = "(?P<service_id>[0-9a-f-]{32,36})"
INSTANCE_UUID = "(?P<instance_id>[0-9a-f-]{32,36})"

urlpatterns = [
    # 平台管理 - 应用列表
    re_path(
        r"^api/plat_mgt/applications/$",
        views.ApplicationListViewSet.as_view({"get": "list"}),
        name="plat_mgt.applications.list_applications",
    ),
    re_path(
        r"^api/plat_mgt/applications/tenant_app_statistics/$",
        views.ApplicationListViewSet.as_view({"get": "list_tenant_app_statistics"}),
        name="plat_mgt.applications.list_tenant_app_statistics",
    ),
    re_path(
        r"^api/plat_mgt/applications/tenant_mode_list/$",
        views.ApplicationListViewSet.as_view({"get": "list_tenant_modes"}),
        name="plat_mgt.applications.list_tenant_modes",
    ),
    re_path(
        r"^api/plat_mgt/applications/types/$",
        views.ApplicationListViewSet.as_view({"get": "list_app_types"}),
        name="plat_mgt.applications.types",
    ),
    # 平台管理 - 应用详情
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/$",
        views.ApplicationDetailViewSet.as_view({"get": "retrieve", "post": "update_app_name"}),
        name="plat_mgt.applications.retrieve_app_name",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/app_category/$",
        views.ApplicationDetailViewSet.as_view({"post": "update_app_category"}),
        name="plat_mgt.applications.update_app_category",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/modules/(?P<module_name>[^/]+)/"
        r"envs/(?P<env_name>[^/]+)/cluster/$",
        views.ApplicationDetailViewSet.as_view({"put": "update_cluster"}),
        name="plat_mgt.applications.update_cluster",
    ),
    # 平台管理 - 应用特性
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/feature_flags/$",
        views.ApplicationFeatureViewSet.as_view({"get": "list", "put": "update"}),
        name="plat_mgt.applications.feature_flags",
    ),
    # 平台管理 - 应用成员
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/members/$",
        views.ApplicationMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="plat_mgt.applications.members",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/members/(?P<user_id>[0-9a-z]+)/?$",
        views.ApplicationMemberViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="plat_mgt.applications.members.detail",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/plugin/members/$",
        BKPluginMembersManageViewSet.as_view({"post": "become_admin", "delete": "remove_admin"}),
        name="plat_mgt.applications.plugin.members.admin",
    ),
    re_path(
        r"^api/plat_mgt/applications/members/roles/$",
        views.ApplicationMemberViewSet.as_view({"get": "get_roles"}),
        name="plat_mgt.applications.members.get_roles",
    ),
    # 平台管理 - 增强服务
    re_path(
        r"^api/plat_mgt/applications/(?P<code>[^/]+)/services/bound_attachments/$",
        views.ApplicationServicesViewSet.as_view({"get": "list_bound_attachments"}),
        name="plat_mgt.applications.services.list_bound_attachments",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<code>[^/]+)/services/unbound_attachments/$",
        views.ApplicationServicesViewSet.as_view({"get": "list_unbound_attachments"}),
        name="plat_mgt.applications.services.list_unbound_attachments",
    ),
    re_path(
        make_app_pattern(
            f"/services/{SERVICE_UUID}/instance/{INSTANCE_UUID}/credentials/$",
            include_envs=True,
            prefix="api/plat_mgt/applications/",
        ),
        views.ApplicationServicesViewSet.as_view({"get": "view_credentials"}),
        name="plat_mgt.applications.services.credentials",
    ),
    re_path(
        make_app_pattern(
            f"/services/{SERVICE_UUID}/instance/{INSTANCE_UUID}/$",
            include_envs=True,
            prefix="api/plat_mgt/applications/",
        ),
        views.ApplicationServicesViewSet.as_view({"delete": "unbound_instance"}),
        name="plat_mgt.applications.services.unbound_instance",
    ),
    re_path(
        make_app_pattern(
            f"/services/{SERVICE_UUID}/instance/$",
            include_envs=True,
            prefix="api/plat_mgt/applications/",
        ),
        views.ApplicationServicesViewSet.as_view({"post": "provision_instance"}),
        name="plat_mgt.applications.services.provision_instance",
    ),
    re_path(
        make_app_pattern(
            f"/services/{SERVICE_UUID}/instance/{INSTANCE_UUID}/$",
            include_envs=False,
            prefix="api/plat_mgt/applications/",
        ),
        views.ApplicationServicesViewSet.as_view({"delete": "recycle_unbound_instance"}),
        name="plat_mgt.applications.services.recycle_unbound_instance",
    ),
    # 平台管理 - 删除应用
    re_path(
        r"^api/plat_mgt/deleted_applications/$",
        views.DeletedApplicationViewSet.as_view({"get": "list"}),
        name="plat_mgt.applications.list_deleted",
    ),
    re_path(
        r"^api/plat_mgt/deleted_applications/(?P<app_code>[^/]+)/$",
        views.DeletedApplicationViewSet.as_view({"delete": "destroy"}),
        name="plat_mgt.applications.force_delete",
    ),
]
