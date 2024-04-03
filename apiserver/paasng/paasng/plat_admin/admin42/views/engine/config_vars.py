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

from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.config_vars import ConfigVarSLZ
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.engine.views import ConfigVarViewSet as BaseConfigVarViewSet

logger = logging.getLogger(__name__)


class ConfigVarManageView(ApplicationDetailBaseView):
    name = "环境变量管理"
    template_name = "admin42/applications/detail/engine/config_var.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        config_vars = ConfigVarSLZ(
            ConfigVar.objects.filter(module__in=application.modules.all()).order_by("module__is_default"), many=True
        ).data
        kwargs["config_vars"] = config_vars
        kwargs["env_choices"] = [{"value": value, "text": text} for value, text in ConfigVarEnvName.get_choices()]
        kwargs["module_list"] = ModuleSLZ(application.modules.all(), many=True).data
        return kwargs


class ConfigVarViewSet(BaseConfigVarViewSet):
    schema = None
    serializer_class = ConfigVarSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_queryset(self):
        application = self.get_application()
        queryset = ConfigVar.objects.filter(module__in=application.modules.all()).order_by("module__is_default")
        return queryset
