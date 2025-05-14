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

from paas_wl.infras.resources.base.kres import BaseKresource


class KServiceMonitor(BaseKresource):
    kind = "ServiceMonitor"


class BkApp(BaseKresource):
    """CRD: App model resource feature"""

    kind = "BkApp"


class DomainGroupMapping(BaseKresource):
    """CRD: Mapping between BkApp and DomainGroups"""

    kind = "DomainGroupMapping"


class GPA(BaseKresource):
    """CRD: General pod autoscaler, powerful than hpa, provided by bcs"""

    kind = "GeneralPodAutoscaler"


class Egress(BaseKresource):
    """CRD: Egress, support fixed egress ip, provided by bcs"""

    kind = "Egress"


class BKLogConfig(BaseKresource):
    """CRD: BkLogConfig is the Schema for the bklogconfigs API"""

    kind = "BkLogConfig"
