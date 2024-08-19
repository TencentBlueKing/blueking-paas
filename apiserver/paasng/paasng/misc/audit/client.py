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

from bk_audit.client import BkAudit
from bk_audit.contrib.bk_audit.settings import bk_audit_settings
from django.conf import settings

logger = logging.getLogger(__name__)

bk_audit_client = BkAudit(
    bk_app_code=settings.BK_APP_CODE,
    bk_app_secret=settings.BK_APP_SECRET,
    settings={
        "log_queue_limit": bk_audit_settings.log_queue_limit,
        "formatter": bk_audit_settings.formatter,
        "exporters": bk_audit_settings.exporters,
        "service_name_handler": bk_audit_settings.service_name_handler,
    },
)
