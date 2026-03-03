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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Literal, Optional

from paas_wl.bk_app.monitoring.bklog.constants import BkLogConfigType
from paas_wl.bk_app.monitoring.bklog.entities import LabelSelector, LogFilterCondition
from paas_wl.bk_app.monitoring.bklog.kres_slzs import BKLogConfigDeserializer, BKLogConfigSerializer
from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models.app import WlApp  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass
class BkAppLogConfig(AppEntity):
    """BkAppLogConfig 蓝鲸日志采集项配置

    :param data_id: 采集项ID
    :param paths: 日志采集路径(s)
    :param filters: bkunifylogbeat filter rule
    :param encoding: 日志编码

    ---
    以下字段由平台控制, 暂不允许用户修改
    :param ext_meta: 日志附带的额外元信息, 例如 {bk_bcs_cluster_id: BCS-K8S-00000}
    :param label_selector: 标签选择器
    :param workload_type: 负载类型, 目前只支持 Deployment
    :
    """

    data_id: int
    paths: List[str]
    filters: Optional[List[LogFilterCondition]] = None
    encoding: str = "utf-8"

    ext_meta: Dict[str, str] = field(default_factory=dict)
    label_selector: LabelSelector = field(default_factory=LabelSelector)
    workload_type: Literal["Deployment"] = "Deployment"
    config_type: BkLogConfigType = BkLogConfigType.CONTAINER_LOG

    class Meta:
        kres_class = crd.BKLogConfig
        deserializer = BKLogConfigDeserializer
        serializer = BKLogConfigSerializer


class BkAppLogConfigManager(AppEntityManager[BkAppLogConfig, "WlApp"]):
    def __init__(self):
        super().__init__(BkAppLogConfig)

    def delete(self, res: BkAppLogConfig, non_grace_period: bool = False):
        namespace = res.app.namespace
        config_name = res.name

        try:
            existed_one = self.get(app=res.app, name=config_name)
        except AppEntityNotFound:
            logger.info("BkLogConfig<%s/%s> does not exist, will skip delete", namespace, config_name)
            return None
        return super().delete(existed_one, non_grace_period)


bklog_config_kmodel = BkAppLogConfigManager()
