# -*- coding: utf-8 -*-
from django.urls import path

from paas_wl.admin.views import certs, clusters, domain, processes

urlpatterns = [
    # 平台管理-应用资源方案-API
    path(
        'admin42/platform/process_spec_plan/manage/',
        processes.ProcessSpecPlanManageViewSet.as_view({"get": "get_context_data"}),
        name="admin.process_spec_plan.manage",
    ),
    path(
        'admin42/platform/process_spec_plan/',
        processes.ProcessSpecPlanManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.process_spec_plan",
    ),
    path(
        'admin42/platform/process_spec_plan/id/<int:id>/',
        processes.ProcessSpecPlanManageViewSet.as_view(dict(put="edit", get="list_binding_app")),
        name="admin.process_spec_plan.detail",
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/plan",
        processes.ProcessSpecManageViewSet.as_view({'put': 'switch_process_plan'}),
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/scale",
        processes.ProcessSpecManageViewSet.as_view({'put': 'scale'}),
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/instances/<str:instance_name>/",
        processes.ProcessInstanceViewSet.as_view({'get': 'retrieve'}),
    ),
    # 独立域名相关 API
    path(
        'admin42/applications/<str:code>/domains/',
        domain.AppDomainsViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='admin.app_domains',
    ),
    path(
        'admin42/applications/<str:code>/domains/<int:id>/',
        domain.AppDomainsViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
        name='admin.app_domains.singular',
    ),
    # Shared certificates
    path(
        'admin42/platform/app_certs/shared/',
        certs.AppDomainSharedCertsViewSet.as_view({'post': 'create', 'get': 'list'}),
    ),
    path(
        'admin42/platform/app_certs/shared/<str:name>',
        certs.AppDomainSharedCertsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
    ),
    # 平台管理-集群管理API
    path(
        'admin42/platform/clusters/',
        clusters.ClusterViewSet.as_view({'post': 'update_or_create', 'get': 'list'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/',
        clusters.ClusterViewSet.as_view({'get': 'retrieve', 'put': 'update_or_create', 'delete': 'destroy'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/api_servers',
        clusters.ClusterViewSet.as_view({'post': 'bind_api_server'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/api_servers/<str:api_server_id>',
        clusters.ClusterViewSet.as_view({'delete': 'unbind_api_server'}),
    ),
]
