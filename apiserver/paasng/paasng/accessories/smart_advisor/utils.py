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

from dataclasses import dataclass
from typing import Any, Dict, List

from django.conf import settings
from django.utils.translation import gettext as _

from paasng.accessories.serializers import DocumentaryLinkSLZ
from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.tagging import get_deployment_tags
from paasng.platform.engine.models.deployment import Deployment
from paasng.utils.text import basic_str_format


@dataclass
class DeploymentFailureHint:
    """A tip object to help user recover from deployment error"""

    matched_solutions_found: bool
    possible_reason: str
    helpers: List[Dict[str, str]]

    def render_links(self, params: Dict[str, Any]):
        """Render helper's "link" field with given params"""
        for helper in self.helpers:
            if "link" in helper:
                helper["link"] = basic_str_format(helper["link"], params)


def get_default_failure_hint() -> DeploymentFailureHint:
    """Make a default failure hint object"""
    helpers = [
        {
            "text": _("日志查询"),
            "link": settings.BKPAAS_URL + "/developer-center/apps/{application_code}/{module_name}/logging?tab=stream",
        },
        {"text": _("去 FAQ 查询试试"), "link": settings.PLATFORM_FAQ_URL},
    ]
    if settings.SUPPORT_LIVE_AGENT:
        helpers.append(settings.LIVE_AGENT_CONFIG)

    return DeploymentFailureHint(
        matched_solutions_found=False,
        possible_reason=_("暂时无法找到解决方案，请前往“标准输出日志”检查是否有异常"),
        helpers=helpers,
    )


def get_failure_hint(deployment: Deployment) -> "DeploymentFailureHint":
    """Get failure hint for deployment"""
    tags = get_deployment_tags(deployment)
    docs = DocumentaryLinkAdvisor().search_by_tags(tags)

    module = deployment.app_environment.module

    link_params = {"application_code": module.application.code, "module_name": module.name}
    if not docs:
        hint = get_default_failure_hint()
        hint.render_links(link_params)
        return hint

    helpers = []
    for doc in docs:
        helpers.append(dict(DocumentaryLinkSLZ(doc).data))
    return DeploymentFailureHint(matched_solutions_found=True, possible_reason=_("已找到解决方案"), helpers=helpers)
