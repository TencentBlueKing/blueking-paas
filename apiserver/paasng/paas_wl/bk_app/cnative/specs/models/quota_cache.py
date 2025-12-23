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

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .res_quota_plan import ResQuotaPlan

CACHE_KEY_ACTIVE_PLANS = "res_quota_plan:active_plans"
CACHE_TIMEOUT = 300  # 5 分钟


def get_active_quota_plans() -> dict[str, ResQuotaPlan]:
    """获取所有激活的资源配额方案，带缓存

    Returns:
        dict: {plan_name: ResQuotaPlan对象}
    """
    plans = cache.get(CACHE_KEY_ACTIVE_PLANS)
    if plans is None:
        plans = {plan.plan_name: plan for plan in ResQuotaPlan.objects.filter(is_active=True)}
        cache.set(CACHE_KEY_ACTIVE_PLANS, plans, timeout=CACHE_TIMEOUT)
    return plans


def clear_quota_plans_cache():
    """清除资源配额方案缓存"""
    cache.delete(CACHE_KEY_ACTIVE_PLANS)


@receiver([post_save, post_delete], sender=ResQuotaPlan)
def invalidate_quota_plans_cache(sender, **kwargs):
    """当 ResQuotaPlan 发生变更时，清除缓存"""
    clear_quota_plans_cache()
