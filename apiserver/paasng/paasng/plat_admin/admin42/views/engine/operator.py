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
from rest_framework.permissions import IsAuthenticated

from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.region.models import get_all_regions
from paasng.utils.configs import get_region_aware


class OperatorManageView(GenericTemplateView):
    """PaaS Operator 管理页"""

    name = "PaaS Operator"
    template_name = "admin42/platformmgr/operator.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self

        cnative_default_cluster = {}
        for region in get_all_regions().keys():
            try:
                cluster_name = get_region_aware('CLOUD_NATIVE_APP_DEFAULT_CLUSTER', region)
            except KeyError:
                cluster_name = '--'
            cnative_default_cluster[region] = cluster_name

        kwargs['cnative_default_cluster'] = cnative_default_cluster
        return kwargs
