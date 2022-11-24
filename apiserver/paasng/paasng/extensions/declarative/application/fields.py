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

from paasng.extensions.declarative.application.constants import APP_NAME_FIELD
from paasng.extensions.declarative.application.validations import ApplicationDesc
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


class AppField:
    """Represents a field in app json data"""

    def __init__(self, application: Application):
        self.application = application

    def handle_desc(self, desc: ApplicationDesc):
        """Handle *incoming* ApplicationDescription"""


class AppNameField(AppField):
    def handle_desc(self, desc: ApplicationDesc):
        if self.application.name != desc.name_zh_cn:
            raise DescriptionValidationError({APP_NAME_FIELD: '该字段不允许被修改'})
        if self.application.name_en != desc.name_en:
            # 允许修改英文名
            logger.warning("应用<%s> 的英文名将从 '%s' 修改成 '%s'", desc.name_zh_cn, self.application.name_en, desc.name_en)
            self.application.name_en = desc.name_en
            self.application.save(update_fields=["name_en", "updated"])


class AppRegionField(AppField):
    def handle_desc(self, desc: ApplicationDesc):
        if desc.region and self.application.region != desc.region:
            raise DescriptionValidationError({'region': '该字段不允许被修改'})
