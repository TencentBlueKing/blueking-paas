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

import logging

from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.engine.constants import AppEnvName

logger = logging.getLogger(__name__)


class LogConfigView(ApplicationDetailBaseView):
    name = "日志采集管理"
    template_name = "admin42/operation/applications/detail/engine/log_config.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["env_choices"] = [{"value": value, "text": text} for value, text in AppEnvName.get_choices()]
        return kwargs
