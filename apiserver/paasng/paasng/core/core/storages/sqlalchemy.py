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

"""Connect to legacy database of PaaS"""

from typing import Any, Dict

from django.conf import settings
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.mapper import Mapper

from .utils import DummyDB, SADBManager

# db engine will be initialize when `engine` property is used.
if getattr(settings, "PAAS_LEGACY_DBCONF", None) is not None:
    legacy_db = SADBManager.get_instance(settings.PAAS_LEGACY_DBCONF)
else:
    legacy_db = DummyDB()


if getattr(settings, "BK_CONSOLE_DBCONF", None) is not None:
    console_db = SADBManager.get_instance(settings.BK_CONSOLE_DBCONF)
else:
    console_db = DummyDB()


# TODO: 先保留 console_db, legacy_db 命名上的差异, 后继再统一删除
if not isinstance(legacy_db, DummyDB):
    console_db = legacy_db
elif not isinstance(console_db, DummyDB):
    legacy_db = console_db


def has_column(sa_model: DeclarativeMeta, name: str) -> bool:
    """Check if an auto-mapped model has a column with given name"""
    mapper: Mapper = inspect(sa_model)
    return name in mapper.columns


def filter_field_values(sa_model: DeclarativeMeta, field_values: Dict[str, Any]) -> Dict[str, Any]:
    """Filter a pair of field values, remove invalid fields"""
    mapper: Mapper = inspect(sa_model)
    return {k: v for k, v in field_values.items() if k in mapper.columns}
