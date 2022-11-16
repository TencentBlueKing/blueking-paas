# -*- coding: utf-8 -*-
import logging

from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.models import RCStateAppBinding, RegionClusterState
from paas_wl.networking.egress.serializers import RCStateAppBindingSLZ
from paas_wl.platform.applications.permissions import AppAction, application_perm_class
from paas_wl.platform.applications.views import ApplicationCodeInPathMixin
from paas_wl.platform.auth.views import BaseEndUserViewSet
from paas_wl.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class EgressGatewayInfosViewSet(BaseEndUserViewSet, ApplicationCodeInPathMixin):
    """应用出口 IP 管理相关 API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def retrieve(self, request, code, module_name, environment):
        """返回已获取的出口网关信息"""
        engine_app = self.get_engine_app_via_path()
        binding = get_object_or_404(RCStateAppBinding, app=engine_app)
        serializer = RCStateAppBindingSLZ(binding)
        return Response(
            {
                # Use 'default' as name of the default egress gateway info for all environments
                'name': 'default',
                'rcs_binding_data': serializer.data,
            }
        )

    def create(self, request, code, module_name, environment):
        """获取应用在该部署环境下的出口网关信息"""
        engine_app = self.get_engine_app_via_path()
        cluster = get_cluster_by_app(engine_app)

        try:
            state = RegionClusterState.objects.filter(region=engine_app.region, cluster_name=cluster.name).latest()
            binding = RCStateAppBinding.objects.create(app=engine_app, state=state)
        except RegionClusterState.DoesNotExist:
            logger.warning('No cluster state can be found for region=%s', engine_app.region)
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("集群数据未初始化，请稍候再试")
        except IntegrityError:
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("不能重复绑定")
        except Exception:
            logger.exception('Unable to crate RCStateBinding instance')
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("请稍候再试")

        serializer = RCStateAppBindingSLZ(binding)
        return Response({'name': 'default', 'rcs_binding_data': serializer.data}, status=status.HTTP_201_CREATED)

    def destroy(self, request, code, module_name, environment):
        """清除已获取的出口网关信息"""
        engine_app = self.get_engine_app_via_path()
        try:
            binding = RCStateAppBinding.objects.get(app=engine_app)
        except RCStateAppBinding.DoesNotExist:
            raise error_codes.ERROR_RECYCLING_EGRESS_GATEWAY_INFO.f("未获取过网关信息")
        binding.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
