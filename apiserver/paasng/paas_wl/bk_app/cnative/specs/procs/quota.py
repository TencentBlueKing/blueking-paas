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
import re

from attrs import asdict, define
from kubernetes.utils import parse_quantity

from paas_wl.bk_app.cnative.specs.constants import (
    DEFAULT_PROC_CPU,
    DEFAULT_PROC_CPU_REQUEST,
    DEFAULT_PROC_MEM,
    DEFAULT_PROC_MEM_REQUEST,
    ResQuotaPlan,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paasng.platform.engine.constants import AppEnvName

logger = logging.getLogger(__name__)


# 自定义资源配额方案的正则表达式
CUSTOM_RESOURCE_QUOTA_PLAN_REGEX = r"^(\d+(?:\.\d+)?)C(\d+(?:\.\d+)?)G$"


@define
class ResourceQuota:
    cpu: str
    memory: str


# 资源配额方案到资源限制的映射表
PLAN_TO_LIMIT_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU,
        memory=DEFAULT_PROC_MEM,
    ),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="4000m", memory="1024Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="4000m", memory="2048Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="4000m", memory="4096Mi"),
}

# 资源配额方案到资源请求的映射表
# CPU REQUEST = 200m
# MEMORY REQUEST 的计算规则: 当 Limits 大于等于 2048 Mi 时，值为 Limits 的 1/2; 当 Limits 小于 2048 Mi 时，值为 Limits 的 1/4
# 云原生应用实际的 requests 配置策略在 operator 中实现, 这里的值并非实际生效值
PLAN_TO_REQUEST_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU_REQUEST,
        memory=DEFAULT_PROC_MEM_REQUEST,
    ),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="200m", memory="256Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="200m", memory="1024Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="200m", memory="2048Mi"),
}


def parse_plan_to_limit_quota(plan: str) -> ResourceQuota:
    """解析资源配额方案为资源限制

    :param plan: 资源配额方案字符串
    :return: ResourceQuota 对象
    """
    try:
        return PLAN_TO_LIMIT_QUOTA_MAP[ResQuotaPlan(plan)]
    except (ValueError, KeyError):
        logger.debug("'%s' is not a predefined quota plan, checking custom format", plan)

    match = re.match(CUSTOM_RESOURCE_QUOTA_PLAN_REGEX, plan, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid custom quota plan format: {plan}")
    cpu_cores, memory_gb = match.group(1), match.group(2)

    cpu_millicores = int(parse_quantity(cpu_cores) * 1000)
    memory_mib = int(parse_quantity(f"{memory_gb}Gi") / (1024 * 1024))

    return ResourceQuota(cpu=f"{cpu_millicores}m", memory=f"{memory_mib}Mi")


def parse_plan_to_request_quota(plan: str) -> ResourceQuota:
    """解析资源配额方案为资源请求

    注意：这里计算的 requests 值仅用于前端展示，实际生效值由 operator 计算

    :param plan: 资源配额方案字符串
    :return: ResourceQuota 对象
    """
    try:
        return PLAN_TO_REQUEST_QUOTA_MAP[ResQuotaPlan(plan)]
    except (ValueError, KeyError):
        logger.debug("'%s' is not a predefined quota plan, checking custom format", plan)

    match = re.match(CUSTOM_RESOURCE_QUOTA_PLAN_REGEX, plan, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid custom quota plan format: {plan}")
    _, memory_gb = match.group(1), match.group(2)

    memory_mib = int(parse_quantity(f"{memory_gb}Gi") / (1024 * 1024))
    if memory_mib >= 2048:
        memory_request_mib = memory_mib // 2
    else:
        memory_request_mib = memory_mib // 4
    return ResourceQuota(cpu="200m", memory=f"{memory_request_mib}Mi")


class ResQuotaReader:
    """Read resQuotaPlan and resQuotas(envOverlay) from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, env_name: AppEnvName) -> dict[str, tuple[dict, bool]]:
        """Read all ResQuota config defined

        :param env_name: Environment name
        :return: Dict[name of process, (config, whether the config was defined in "envOverlay")],
          config is {"plan": plan name, "limits": {"cpu":cpu limit, "memory": memory limit},
          "requests": {"cpu":cpu request, "memory": memory request}}
        """
        results: dict[str, tuple[dict, bool]] = {}
        for p in self.res.spec.processes:
            plan = p.resQuotaPlan or ResQuotaPlan.P_DEFAULT.value
            limit_quota = parse_plan_to_limit_quota(plan)
            request_quota = parse_plan_to_request_quota(plan)

            results[p.name] = (
                {
                    "plan": str(plan),
                    "limits": asdict(limit_quota),
                    # TODO 云原生应用的 requests 取值策略在 operator 中实现. 这里的值并非实际生效值, 仅用于前端展示. 如果需要, 后续校正?
                    "requests": asdict(request_quota),
                },
                False,
            )

        if overlay := self.res.spec.envOverlay:
            quotas_overlay = overlay.resQuotas or []
        else:
            quotas_overlay = []

        for quotas in quotas_overlay:
            if quotas.envName == env_name:
                limit_quota = parse_plan_to_limit_quota(quotas.plan)
                request_quota = parse_plan_to_request_quota(quotas.plan)

                results[quotas.process] = (
                    {
                        "plan": quotas.plan,
                        "limits": asdict(limit_quota),
                        "requests": asdict(request_quota),
                    },
                    True,
                )

        return results


def is_available_res_quota_plan(plan: str) -> bool:
    """检查 plan 是否有效

    支持两种类型的方案:
    1. 预定义方案: default, 4C1G, 4C2G, 4C4G
    2. 自定义方案: 格式为 {cpu}C{memory}G, 如 2C4G

    :param plan: 资源配额方案字符串
    :return: 是否有效
    """
    if not plan:
        return False

    # 检查是否为预定义方案
    try:
        ResQuotaPlan(plan)
    except ValueError:
        logger.debug("'%s' is not a predefined quota plan, checking custom format", plan)
    else:
        return True

    # 检查是否为自定义方案
    match = re.match(CUSTOM_RESOURCE_QUOTA_PLAN_REGEX, plan, re.IGNORECASE)
    if not match:
        return False

    cpu_cores, memory_gb = match.group(1), match.group(2)
    try:
        parse_quantity(cpu_cores)
        parse_quantity(f"{memory_gb}Gi")
    except ValueError:
        logger.debug("Invalid custom quota plan format '%s': failed to parse resource quantities", plan)
        return False
    else:
        return True
