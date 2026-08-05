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

from django.apps import AppConfig


class VendorConfig(AppConfig):
    name = "svc_bk_repo.vendor"

    def ready(self):
        # 统一调度器启动入口: 在此显式导入所有需要注册的定时任务模块.
        import svc_bk_repo.monitoring.jobs
        import svc_bk_repo.vendor.jobs  # noqa: F401
        from svc_bk_repo.shared.scheduler import start_scheduler

        start_scheduler()
