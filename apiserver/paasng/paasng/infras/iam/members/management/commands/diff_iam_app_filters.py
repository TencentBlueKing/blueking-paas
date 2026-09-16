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

"""对账同一批用户在权限中心 V3 与 V4 下能看到的应用列表

用于 V4 灰度切换前的等价性验证：两个版本的授权数据互相隔离，只有逐用户比对列表结果
才能确认策略下推的改造没有少显或多显应用。仅供测试环境使用，不进入任何请求路径。

请挑选确实有应用权限的用户来跑：两侧都取不到策略的用户什么也验证不了，会被记为
inconclusive 并让命令以非 0 退出，避免把「什么都没验证」当成通过。

Examples:

    # 比对指定用户能看到的应用（默认比对基础信息查看权限，即应用列表页的口径）
    python manage.py diff_iam_app_filters --users user1 user2

    # 比对开发者应用列表的口径
    python manage.py diff_iam_app_filters --users user1 --action basic_develop

    # 指定租户，默认取初始租户
    python manage.py diff_iam_app_filters --users user1 --tenant-id tenant-foo
"""

import traceback
from typing import List, Optional, Set

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.iam.v3.auth import BKIAMV3AuthBackend
from paasng.infras.iam.v4.auth import BKIAMV4AuthBackend
from paasng.platform.applications.models import Application

# 应用列表页与开发者应用列表页各自下推的操作，即 `_gen_app_filters` 的两种入参
COMPARABLE_ACTIONS = [AppAction.VIEW_BASIC_INFO, AppAction.BASIC_DEVELOP]

# 与 `_gen_app_filters` 保持一致的字段映射。V4 会忽略它，V3 的 SDK converter 需要
APP_KEY_MAPPING = {"application.id": "code"}

# 差异明细的最大打印条数。大权限账号的差异可能有几千条，全量打进流水线日志没有意义
DIFF_DISPLAY_LIMIT = 50


class Command(BaseCommand):
    help = "Diff the application list a user can see between iam v3 and v4"

    def add_arguments(self, parser):
        parser.add_argument("--users", dest="usernames", nargs="+", required=True, help="待比对的用户名列表")
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="租户标识，默认取初始租户")
        parser.add_argument(
            "--action",
            dest="action_id",
            default=AppAction.VIEW_BASIC_INFO.value,
            # 取 .value 而非枚举成员：AppAction 本质是 str，直接传能跑通，
            # 但 argparse 会把 --help 与报错里的候选渲染成枚举 repr，照着拷贝会传错
            choices=[action.value for action in COMPARABLE_ACTIONS],
            help="比对哪个操作下的应用列表",
        )

    def handle(self, usernames: List[str], tenant_id: str, action_id: str, *args, **options):
        tenant_id = tenant_id or get_init_tenant_id()

        v3_backend, v4_backend = BKIAMV3AuthBackend(), BKIAMV4AuthBackend()

        print(  # noqa: T201
            f"---- diff app list between iam v3 and v4 for {len(usernames)} user(s), "
            f"tenant: {tenant_id}, action: {action_id} ----"
        )

        identical, diff_usernames, inconclusive_usernames, failed_usernames = 0, [], [], []

        for idx, username in enumerate(usernames, start=1):
            prefix = f"{idx}/{len(usernames)} {username}"

            try:
                v3_codes = self._authorized_app_codes(v3_backend, action_id, username, tenant_id)
                v4_codes = self._authorized_app_codes(v4_backend, action_id, username, tenant_id)
            except Exception as e:  # noqa: BLE001
                # 这里兜的是数据库等本地故障。权限中心侧的失败不会抛到这里，
                # 它在两个 backend 内部都被折成 None，由下面的 inconclusive 分支识别
                failed_usernames.append(username)
                print(f"{prefix}: ERROR {e}")  # noqa: T201
                print(traceback.format_exc())  # noqa: T201
                continue

            # 任一侧取不到策略就无从比对：拿到的不是「没有应用」，而是「不知道有哪些应用」。
            # 两个 backend 在权限中心报错时都返回 None，若把它当成空集，一侧故障会表现为
            # 「两边都是 0 个应用、结果一致」，门禁就成了虚假的绿灯
            if v3_codes is None or v4_codes is None:
                unknown = [version for version, codes in (("v3", v3_codes), ("v4", v4_codes)) if codes is None]
                inconclusive_usernames.append(username)
                print(f"{prefix}: INCONCLUSIVE, no policy obtained from {unknown}")  # noqa: T201
                continue

            v3_only = sorted(v3_codes - v4_codes)
            v4_only = sorted(v4_codes - v3_codes)

            if not (v3_only or v4_only):
                identical += 1
                print(f"{prefix}: identical, {len(v3_codes)} app(s)")  # noqa: T201
                continue

            diff_usernames.append(username)
            print(f"{prefix}: DIFF, v3 {len(v3_codes)} app(s) / v4 {len(v4_codes)} app(s)")  # noqa: T201
            print(f"{' ' * len(prefix)}  v3 has but v4 misses: {self._summarize(v3_only)}")  # noqa: T201
            print(f"{' ' * len(prefix)}  v4 has but v3 misses: {self._summarize(v4_only)}")  # noqa: T201

        print(  # noqa: T201
            f"---- total: {len(usernames)}, identical: {identical}, different: {len(diff_usernames)}, "
            f"inconclusive: {len(inconclusive_usernames)}, failed: {len(failed_usernames)} ----"
        )

        # 以非 0 退出码结束，便于在流水线里直接作为切换前的门禁。inconclusive 同样算不通过：
        # 它代表这一轮对账没有验证到任何东西
        if diff_usernames or inconclusive_usernames or failed_usernames:
            raise CommandError(
                f"different: {diff_usernames}, inconclusive: {inconclusive_usernames}, failed: {failed_usernames}"
            )

    @staticmethod
    def _authorized_app_codes(
        backend: BaseAuthBackend, action_id: str, username: str, tenant_id: str
    ) -> Optional[Set[str]]:
        """查询该用户在此版本下有权限的应用 code，未取得策略时返回 None

        直接调 `build_resource_filter` 而不是复用 `ApplicationPermission.gen_user_app_filters`：
        后者会把「未取得策略」折成豁免过滤器，于是权限中心故障与「确实只剩自建应用」在结果上
        无从分辨。顺带也排除了豁免窗口——它只与时间和创建人有关，两侧必然一致，纳入比对
        只会让差异夹进与权限无关的噪声。
        """
        filters = backend.build_resource_filter(username, tenant_id, action_id, key_mapping=APP_KEY_MAPPING)
        if not filters:
            return None

        # 与列表页一致地叠加租户过滤，否则别的租户的应用会被算进差异。
        # Application 的默认 manager 已排除软删除的应用，无需再过滤
        return set(Application.objects.filter(filters & Q(tenant_id=tenant_id)).values_list("code", flat=True))

    @staticmethod
    def _summarize(codes: List[str]) -> str:
        if len(codes) <= DIFF_DISPLAY_LIMIT:
            return str(codes)

        return f"{codes[:DIFF_DISPLAY_LIMIT]} ... ({len(codes)} in total)"
