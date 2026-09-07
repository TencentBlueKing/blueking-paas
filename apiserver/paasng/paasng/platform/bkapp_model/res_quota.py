# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from typing import Iterable

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from paasng.platform.bkapp_model.models import ModuleProcessSpec, ResQuotaPlan
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module

# 统一错误语义：不存在 / 停用 / 不在白名单，都不泄露名单内容
PLAN_UNAVAILABLE = _("资源配额方案不可用")


class ResQuotaPlanPolicy:
    """资源配额方案的可见与分配策略。

    空名单 = 公开；非空 = 仅名单内 app_code 可新选。先看 is_active，再看白名单。
    进程已绑定的方案允许保留，即使已停用或被移出名单。
    """

    def normalize_allowed_app_codes(self, codes: Iterable | None) -> list[str]:
        """去空白、去重、保序。空白项丢弃。"""
        if not codes:
            return []

        seen: set[str] = set()
        result: list[str] = []
        for raw in codes:
            if raw is None:
                continue
            item = str(raw).strip()
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    def can_select(self, plan: ResQuotaPlan, app_code: str | None) -> bool:
        """方案是否可被该应用新选。无 app_code 时仅公开方案可选。"""
        if not plan.is_active:
            return False
        codes = plan.allowed_app_codes or []
        if not codes:
            return True
        if not app_code:
            return False
        return app_code in codes

    def can_assign(self, plan_name: str, app_code: str | None, current_plan_name: str | None = None) -> bool:
        """新选必须可新选；与当前方案同名则只要方案仍存在即可保留。"""
        if current_plan_name == plan_name:
            return ResQuotaPlan.objects.filter(name=plan_name).exists()

        try:
            plan = ResQuotaPlan.objects.get(name=plan_name)
        except ResQuotaPlan.DoesNotExist:
            return False
        return self.can_select(plan, app_code)

    def ensure_assignable(
        self, plan_name: str | None, app_code: str | None, current_plan_name: str | None = None
    ) -> None:
        """不可分配时抛出不泄露白名单的 ValidationError。"""
        if not plan_name:
            return
        if not self.can_assign(plan_name, app_code, current_plan_name):
            raise ValidationError(PLAN_UNAVAILABLE)

    def list_selectable(self, app_code: str | None = None) -> list[ResQuotaPlan]:
        """已启用且对该应用可新选的方案。无 app_code 时只返回公开方案。"""
        return [
            plan
            for plan in ResQuotaPlan.objects.filter(is_active=True).order_by("created")
            if self.can_select(plan, app_code)
        ]

    def bound_env_plans(self, module: Module) -> dict[tuple[str, str], str | None]:
        """(process_name, env_name) -> 当前生效的 plan_name（含 overlay 回落）。"""
        result: dict[tuple[str, str], str | None] = {}
        specs = ModuleProcessSpec.objects.filter(module=module).prefetch_related("env_overlays")
        for spec in specs:
            for env_name in AppEnvName:
                result[(spec.name, env_name.value)] = spec.get_plan_name(env_name)
        return result

    def bound_plans(self, module: Module) -> dict[tuple[str, str | None], str | None]:
        """(process_name, env_name|None) -> plan_name。None 表示进程级方案。"""
        result: dict[tuple[str, str | None], str | None] = {}
        specs = ModuleProcessSpec.objects.filter(module=module).prefetch_related("env_overlays")
        for spec in specs:
            result[(spec.name, None)] = spec.plan_name
            for overlay in spec.env_overlays.all():
                result[(spec.name, overlay.environment_name)] = overlay.plan_name
        return result

    def bound_overrides(self, proc_spec: ModuleProcessSpec) -> dict[str, str | None]:
        """env_name -> 平台运营 override_plan_name。"""
        return {overlay.environment_name: overlay.override_plan_name for overlay in proc_spec.env_overlays.all()}
