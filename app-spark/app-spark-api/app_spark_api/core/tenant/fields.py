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

"""Custom fields related with multi-tenancy."""

from django.db import models

from .user import DEFAULT_TENANT_ID


def tenant_id_field_factory(db_index: bool = True, unique: bool = False) -> models.CharField:
    """Create a field that is configured to store tenant_id.

    :param db_index: Whether to create an index for the field, defaults to True, turn
        it off when the model already has a compound index on the tenant_id field.
    :param unique: Whether to create a unique index for the field, defaults to False.

    NOTE: https://github.com/TencentBlueKing/blueking-paas/pull/1877#discussion_r1912873811 中有相关的设计讨论
    """
    # If unique is True, db_index should be disabled to avoid creating a redundant index.
    if unique:
        db_index = False
    return models.CharField(
        verbose_name="租户 ID",
        max_length=32,
        default=DEFAULT_TENANT_ID,
        help_text="本条数据的所属租户",
        db_index=db_index,
        unique=unique,
    )
