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

from django.conf import settings

from paas_wl.monitoring.bklog.constants import BkLogConfigType
from paas_wl.monitoring.bklog.entities import BkAppLogConfig, bklog_config_kmodel
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.models import CustomCollectorConfig

logger = logging.getLogger(__name__)


def build_bklog_config_crd(wl_app: WlApp, custom_collector_config: CustomCollectorConfig) -> BkAppLogConfig:
    return BkAppLogConfig(
        app=wl_app,
        name=custom_collector_config.name_en.replace("_", "-"),
        data_id=custom_collector_config.bk_data_id,
        paths=custom_collector_config.log_paths,
        ext_meta={},
        config_type=BkLogConfigType.CONTAINER_LOG
        if custom_collector_config.log_type == "json"
        else BkLogConfigType.STD_LOG,
    )


def make_bk_log_controller(wl_app: WlApp):
    if not settings.ENABLE_BK_LOG:
        logger.warning("BkLog is not ready, skip apply BkLogConfig")
        return NullController()
    else:
        return AppLogConfigController(wl_app)


class AppLogConfigController:
    def __init__(self, wl_app: WlApp):
        self.wl_app = wl_app
        self.module = ModuleEnvironment.objects.get(engine_app_id=wl_app.uuid).module
        self.db_collector_configs = CustomCollectorConfig.objects.filter(module=self.module)

    def create_or_patch(self):
        if self.db_collector_configs.count() == 0:
            return

        for collector_config in self.db_collector_configs:
            bklog_config = build_bklog_config_crd(self.wl_app, collector_config)
            try:
                existed = bklog_config_kmodel.get(app=bklog_config.app, name=bklog_config.name)
            except AppEntityNotFound:
                bklog_config_kmodel.save(bklog_config)
                continue

            if existed != bklog_config:
                # DynamicClient 默认使用 strategic-merge-patch, CRD 不支持, 因此需要使用 merge-patch
                bklog_config_kmodel.update(
                    bklog_config, update_method='patch', content_type="application/merge-patch+json"
                )

    def remove(self):
        if self.db_collector_configs.count() == 0:
            return

        for collector_config in self.db_collector_configs:
            bklog_config = build_bklog_config_crd(self.wl_app, collector_config)
            bklog_config_kmodel.delete(bklog_config)


class NullController:
    def create_or_patch(self):
        ...

    def remove(self):
        ...
