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

"""Utils for legacy platform"""
import re
from typing import Any, List, Optional

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from sqlalchemy.orm import Query, Session

from paasng.core.region.models import get_all_regions

try:
    from paasng.infras.legacydb_te.models import get_developers_by_v2_application
except ImportError:
    from paasng.infras.legacydb.models import get_developers_by_v2_application


RE_QQ = re.compile(r"^\d{5,}$")


def build_legacy_region_maps():
    return {config.basic_info.legacy_deploy_version: region for region, config in get_all_regions().items()}


_region_map = SimpleLazyObject(build_legacy_region_maps)


class LegacyAppNormalizer:
    """Normalize legacy application object"""

    def __init__(self, app: Any):
        self.app = app

    def get_region(self) -> Optional[str]:
        """Get region"""
        if hasattr(self.app, "deploy_ver"):
            return _region_map.get(self.app.deploy_ver)
        else:
            return settings.DEFAULT_REGION_NAME

    def get_developers(self) -> List[str]:
        """Get app's developers list, the results will be cached in memory"""
        if not getattr(self, "_cached_developers", None):
            developers = get_developers_by_v2_application(self.app)
            # Skip external developers which is QQ number
            self._cached_developers = [u for u in developers if not RE_QQ.match(u)]
        return self._cached_developers

    def get_creator(self) -> str:
        """Get app's creator"""
        # "creater" is not a typo
        creator = self.app.creater or ""
        if RE_QQ.match(creator):
            developers = self.get_developers()
            if developers:
                return developers[0]
        return creator

    def get_logo_url(self) -> str:
        """Return app's logo url"""
        # Always return the default logo
        return settings.APPLICATION_DEFAULT_LOGO


def query_concrete_apps(session: Session, model: Any) -> Query:
    """Return a sqlalchemy query for querying concrete apps."""
    query = session.query(model).filter(
        # `app_type` was not added in query fields, all types will be included
        model.from_paasv3 == 0,
        model.migrated_to_paasv3 == 0,
        model.is_lapp == 0,
    )
    return query
