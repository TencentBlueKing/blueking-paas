# -*- coding: utf-8 -*-
from paas_wl.utils.basic import make_app_path, re_path

from . import views_enduser

urlpatterns = [
    re_path(
        make_app_path(r'/egress_gateway_infos/$'),
        views_enduser.EgressGatewayInfosViewSet.as_view({'post': 'create'}),
        name='api.egress_gateway_infos',
    ),
    re_path(
        make_app_path(r'/egress_gateway_infos/default/$'),
        views_enduser.EgressGatewayInfosViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='api.egress_gateway_infos.default',
    ),
]
