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

from django.conf import settings
from rest_framework.permissions import IsAuthenticated

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.constants import ClusterType


class ClusterManageView(GenericTemplateView):
    """Cluster 管理页"""

    name = "集群管理"
    template_name = "admin42/platformmgr/clusters.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        if "view" not in kwargs:
            kwargs["view"] = self

        kwargs.update(
            {
                "region_list": [
                    {"value": region.name, "text": region.display_name} for region in get_all_regions().values()
                ],
                "cluster_type_list": [
                    {"value": value, "text": display_name} for value, display_name in ClusterType.get_choices()
                ],
                "feature_flag_list": [
                    {"value": value, "text": display_name}
                    for value, display_name in ClusterFeatureFlag.get_django_choices()
                ],
            }
        )
        return kwargs


class ClusterComponentManageView(GenericTemplateView):
    """集群组件页面"""

    name = "集群组件"
    template_name = "admin42/platformmgr/cluster_components.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        if "view" not in kwargs:
            kwargs["view"] = self

        kwargs["cluster_components"] = settings.BKPAAS_K8S_CLUSTER_COMPONENTS
        return kwargs
