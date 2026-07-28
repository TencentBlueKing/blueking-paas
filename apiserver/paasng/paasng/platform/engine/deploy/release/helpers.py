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

import logging

from paas_wl.bk_app.monitoring.bklog.shim import make_bk_log_controller
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def ensure_namespace(env: ModuleEnvironment, max_wait_seconds: int = 15) -> bool:
    """确保命名空间存在, 如果命名空间不存在, 那么将创建一个 Namespace 和 ServiceAccount

    :param env: ModuleEnvironment
    :param max_wait_seconds: 等待 ServiceAccount 就绪的时间
    :return: whether an namespace was created.
    """
    wl_app = env.wl_app
    with get_client_by_app(wl_app) as client:
        namespace_client = KNamespace(client)
        _, created = namespace_client.get_or_create(name=wl_app.namespace)
        if created:
            namespace_client.wait_for_default_sa(namespace=wl_app.namespace, timeout=max_wait_seconds)
        return created


def ensure_bk_log_if_need(env: ModuleEnvironment):
    """如果集群支持且应用声明了 BkLogConfig, 则尝试下发日志采集配置"""
    try:
        # 下发 BkLogConfig
        make_bk_log_controller(env).create_or_patch()
    except Exception:
        logger.exception("An error occur when creating BkLogConfig")
