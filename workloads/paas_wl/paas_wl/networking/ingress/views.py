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
import logging

from rest_framework.response import Response

from paas_wl.networking.ingress.exceptions import EmptyAppIngressError
from paas_wl.platform.applications.models import Release
from paas_wl.platform.system_api.views import SysAppRelatedViewSet
from paas_wl.utils.error_codes import error_codes

from .exceptions import DefaultServiceNameRequired
from .managers import AppDefaultIngresses

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
