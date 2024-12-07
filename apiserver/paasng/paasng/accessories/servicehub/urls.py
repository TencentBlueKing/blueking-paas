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

REGION = "(?P<region>[a-z0-9_-]{1,32})"
SERVICE_UUID = "(?P<service_id>[0-9a-f-]{32,36})"
APP_UUID = "(?P<application_id>[0-9a-f-]{32,36})"
CATEGORY_ID = r"(?P<category_id>[\d]+)"

urlpatterns = [
    # service APIs
    re_path(
        r"^api/services/%s/$" % SERVICE_UUID,
        views.ServiceViewSet.as_view({"get": "retrieve"}),
        name="api.services.get_service_detail",
    ),
    re_path(
        r"^api/services/regions/%s/$" % REGION,
        views.ServiceViewSet.as_view({"get": "list_by_region"}),
        name="api.services.list_service_by_region",
    ),
    re_path(
        r"^api/services/regions/%s/init_templates/(?P<template>[\w-]+)$" % REGION,
        views.ServiceViewSet.as_view({"get": "list_by_template"}),
        name="api.services.list_service_by_template",
    ),
    re_path(
        r"^api/services/%s/application-attachments/$" % SERVICE_UUID,
        views.ServiceViewSet.as_view({"get": "list_related_apps"}),
        name="api.services.list_application",
    ),
    re_path(
        r"^api/services/%s/regions/%s/specs$" % (SERVICE_UUID, REGION),
        views.ServicePlanViewSet.as_view({"get": "retrieve_specifications"}),
        name="api.services.get_specifications",
    ),
    re_path(
        f"^api/services/categories/{CATEGORY_ID}/$",
        views.ServiceSetViewSet.as_view({"get": "list_by_category"}),
        name="api.services.list_service_by_category",
    ),
    # List attachments (from service side)
    re_path(
        r"^api/services/name/(?P<service_name>[\w-]+)/application-attachments/$",
        views.ServiceSetViewSet.as_view({"get": "list_by_name"}),
        name="api.services.list_service_with_application",
    ),
    # List attachments (from app side)
    # [Deprecated] use api.services.list_by_module instead
    re_path(
        make_app_pattern(f"/services/categories/{CATEGORY_ID}/$", include_envs=False),
        views.ServiceViewSet.as_view({"get": "list_by_category"}),
        name="api.services.list_by_application",
    ),
    re_path(
        make_app_pattern("/services/$", include_envs=False),
        views.ServiceViewSet.as_view({"get": "list_by_module"}),
        name="api.services.list_by_module",
    ),
    re_path(
        make_app_pattern("/services/attachments/"),
        views.ModuleServiceAttachmentsViewSet.as_view({"get": "list"}),
        name="api.modules.services.attachments",
    ),
    re_path(
        make_app_pattern("/services/info/", include_envs=False),
        views.ModuleServiceAttachmentsViewSet.as_view({"get": "retrieve_info"}),
        name="api.modules.services.info",
    ),
    re_path(
        make_app_pattern("/services/config_var_keys/$", include_envs=False),
        views.ModuleServicesViewSet.as_view({"get": "list_provisioned_env_keys"}),
        name="api.services.list_provisioned_env_keys",
    ),
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/specs$", include_envs=False),
        views.ModuleServicesViewSet.as_view({"get": "retrieve_specs"}),
        name="api.services.list_specs_by_application",
    ),
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/$", include_envs=False),
        views.ModuleServicesViewSet.as_view({"get": "retrieve", "delete": "unbind"}),
        name="api.services.list_by_application",
    ),
    # Manager service attachments (from services side)
    re_path(
        r"^api/services/service-attachments/$",
        views.ModuleServicesViewSet.as_view({"post": "bind"}),
        name="api.services.service_application_attachments.bind",
    ),
    # Manager engine_app attachment
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/credentials_enabled/$", include_envs=False),
        views.ServiceEngineAppAttachmentViewSet.as_view({"get": "list", "put": "update"}),
        name="api.services.credentials_enabled",
    ),
    # List unbound engine_app attachment instances, and recycle instance
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/service/attachment/instances/unbound/$",
        views.UnboundServiceEngineAppAttachmentViewSet.as_view({"get": "list", "post": "recycle_instance"}),
        name="api.services.attachment.unbound",
    ),
    # Service sharing APIs
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/shareable_modules/$", include_envs=False),
        views.ServiceSharingViewSet.as_view({"get": "list_shareable"}),
        name="api.services.list_shareable_modules",
    ),
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/shared_attachment$", include_envs=False),
        views.ServiceSharingViewSet.as_view({"get": "retrieve", "post": "create_shared", "delete": "destroy"}),
        name="api.services.shared_attachment",
    ),
    re_path(
        make_app_pattern(f"/services/{SERVICE_UUID}/sharing_references/related_modules/$", include_envs=False),
        views.SharingReferencesViewSet.as_view({"get": "list_related_modules"}),
        name="api.services.sharing_references.list_related_modules",
    ),
    # Retrieve application information related to the mysql db_name
    re_path(
        r"^sys/api/services/mysql/(?P<db_name>[^/]+)/related_applications_info/$",
        views.RelatedApplicationsInfoViewSet.as_view({"get": "retrieve_related_applications_info"}),
        name="api.services.mysql.retrieve_related_applications_info",
    ),
]

# Multi-editions specific start

try:
    from .urls_ext import urlpatterns as urlpatterns_ext

    urlpatterns += urlpatterns_ext
except ImportError:
    pass

# Multi-editions specific end
