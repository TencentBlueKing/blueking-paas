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
from typing import Dict

from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource

logger = logging.getLogger(__name__)


class ResourceQuotaReader:
    """Read ResourceQuota (limit) from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self) -> Dict[str, Dict[str, str]]:
        """Read all resource quota defined

        :returns: A dict contains resource limit for all processes, value format: {"cpu": "1000m", "memory": "128Mi"}
        """
        return {p.name: {"cpu": p.cpu, "memory": p.memory} for p in self.res.spec.processes}
