# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.exceptions import EmptyAppIngressError
from paas_wl.platform.applications.models import EngineApp, Release
from paas_wl.platform.applications.struct_models import get_structured_app
from paas_wl.platform.system_api.views import SysAppRelatedViewSet, SysModelViewSet
from paas_wl.utils.error_codes import error_codes

from .exceptions import DefaultServiceNameRequired
from .managers import AppDefaultIngresses, assign_custom_hosts, assign_subpaths
from .models import AppDomain, AppDomainSharedCert, AppSubpath, AutoGenDomain, Domain
from .serializers import (
    AppDomainSharedCertSLZ,
    AppDomainSLZ,
    AppSubpathSLZ,
    UpdateAppDomainSharedCertSLZ,
    UpdateAppSubpathsSLZ,
    UpdateAutoGenAppDomainsSLZ,
)
from .utils import guess_default_service_name

logger = logging.getLogger(__name__)


class ProcIngressViewSet(SysAppRelatedViewSet):
    """Manages app's ProcIngress resources"""

    def sync(self, request, region, name):
        """Manually sync app's Ingress resources, usually called after app's metadata has been updated"""
        app = self.get_app()
        # Skip when app has not been released yet
        if not Release.objects.any_successful(app):
            return Response({})

        for mgr in AppDefaultIngresses(app).list():
            try:
                mgr.sync()
            except (DefaultServiceNameRequired, EmptyAppIngressError):
                continue
            except Exception:
                logger.exception('Fail to sync Ingress for %s', app)
                raise error_codes.SYNC_INGRESSES_ERROR.f('请稍候重试')
        return Response({})


class AppDomainViewSet(SysAppRelatedViewSet):
    """A viewset for managing AppDomains"""

    def list(self, request, region, name):
        """list an app's domains, the results will include both domains created by paasng
        system(CUSTOM) and those created by user(INDEPENDENT)
        """
        app = self.get_app()
        domains = AppDomain.objects.filter(app=app).order_by('source')
        return Response(AppDomainSLZ(domains, many=True).data)

    @transaction.atomic
    def update(self, request, region, name):
        """Assign domains to an app, this API was original designed to be used by paasng system
        only, if an user wants to create his own custom domain, see custom domain instead.
        """
        app = self.get_app()
        serializer = UpdateAutoGenAppDomainsSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        default_service_name = guess_default_service_name(app)

        # Assign domains to app
        domains = [AutoGenDomain(**d) for d in data['domains']]
        assign_custom_hosts(app, domains=domains, default_service_name=default_service_name)
        return Response(serializer.data)


class AppDomainSharedCertsViewSet(SysModelViewSet):
    """A viewset for managing app certificates"""

    lookup_field = 'name'
    model = AppDomainSharedCert
    serializer_class = AppDomainSharedCertSLZ
    pagination_class = None
    queryset = AppDomainSharedCert.objects.all()

    @transaction.atomic
    def update(self, request, name):
        """Update a shared certificate"""
        cert = get_object_or_404(AppDomainSharedCert, name=name)
        serializer = UpdateAppDomainSharedCertSLZ(cert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # TODO: Find all appdomain which is using this certificate, refresh their secret resources
        return Response(self.serializer_class(cert).data)


class AppSubpathViewSet(SysAppRelatedViewSet):
    """A viewset for managing application's subpaths"""

    def list(self, request, region, name):
        """list an app's subpaths"""
        app = self.get_app()
        subpaths = AppSubpath.objects.filter(app=app).order_by('source')
        return Response(AppSubpathSLZ(subpaths, many=True).data)

    @transaction.atomic
    def update(self, request, region, name):
        """assign subpaths to an app"""
        app = self.get_app()
        serializer = UpdateAppSubpathsSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        default_service_name = guess_default_service_name(app)

        # Assign subpaths to app
        subpaths = [d['subpath'] for d in data['subpaths']]
        assign_subpaths(app, subpaths, default_service_name=default_service_name)
        return Response(serializer.data)


class AppCustomDomainViewSet(SysAppRelatedViewSet):
    """A viewset managing app's custom domains"""

    def list(self, request, code):
        """Get application's all custom domains"""
        struct_app = get_structured_app(code=code)
        results = []
        for domain in Domain.objects.filter(module_id__in=struct_app.module_ids):
            env = struct_app.get_env_by_id(domain.environment_id)
            engine_app = EngineApp.objects.get(pk=env.engine_app_id)
            port_map = get_cluster_by_app(engine_app).ingress_config.port_map
            port = port_map.get_port_num(domain.protocol)

            results.append(
                {
                    'module_id': domain.module_id,
                    'environment_id': domain.environment_id,
                    'domain_url': {
                        'protocol': domain.protocol,
                        'hostname': domain.name,
                        'port': port,
                        'path_prefix': domain.path_prefix,
                    },
                }
            )
        return Response(results)
