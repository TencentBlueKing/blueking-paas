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
from typing import List

from paasng.platform.evaluation.constants import EmailReceiverType

logger = logging.getLogger(__name__)


class AppOperationReportNotifier:
    """将蓝鲸应用的运营报告发送到指定对象"""

    def send(self, receiver_type: EmailReceiverType, receivers: List[str]):
        # 该版本暂时不支持发送邮件，有需要可以在 notifiers_ext 中实现同名类
        logger.warning("send operation report is unsupported")


try:
    from .notifiers_ext import *  # type: ignore
except ImportError:
    pass
