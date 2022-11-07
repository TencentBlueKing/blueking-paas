# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

from .serializers import DocumentaryLinkSLZ, ListAdvisedDocLinksSLZ
from .smart_advisor import force_tag, get_default_tagset
from .smart_advisor.advisor import DocumentaryLinkAdvisor
from .smart_advisor.models import get_tags

logger = logging.getLogger(__name__)


class AdvisedDocumentaryLinksViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for documentary links"""

    # serializer_class = DocumentaryLinkSLZ
    permission_classes = [IsAuthenticated, application_perm_class('view_application')]

    def list(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)

        slz = ListAdvisedDocLinksSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        plat_panel_tag = get_default_tagset().get(slz.data["plat_panel"])

        tags = get_tags(module)
        # Use tag from application language if no tags can be found in database
        if not tags:
            try:
                tags.add(force_tag("app-pl:{}".format(application.language.lower())))
            except Exception:
                logger.exception("Unable to create tag from application language")
        tags.add(plat_panel_tag)

        advisor = DocumentaryLinkAdvisor()
        links = advisor.search_by_tags(tags, limit=slz.data["limit"])
        return Response({'links': DocumentaryLinkSLZ(links, many=True).data})
