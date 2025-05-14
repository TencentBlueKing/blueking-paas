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
from typing import Any, List

from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import CursorWrapper
from django.db.models import Model

logger = logging.getLogger(__name__)


def copy_field(app_label: str, model_name: str, from_field: str, to_field: str, batch_size: int = 2000):
    def migrate(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
        model = apps.get_model(app_label, model_name)
        bulk_update_chunk_by_chunk(
            schema_editor, model, from_field=from_field, to_field=to_field, batch_size=batch_size
        )

    return migrate


def bulk_update_chunk_by_chunk(
    schema_editor: BaseDatabaseSchemaEditor, model: Model, from_field: str, to_field: str, batch_size: int
):
    quote_name = schema_editor.connection.ops.quote_name
    table_name = quote_name(model._meta.db_table)
    pk_field = quote_name(model._meta.pk.name)

    if not table_name:
        raise RuntimeError(f"Can't get table name from django model<{model.__name__}>!")
    if not pk_field:
        raise RuntimeError(f"Can't get pk field from django model<{model.__name__}>!")

    statement_tmpl = (
        f"UPDATE {table_name} SET {quote_name(to_field)} = {quote_name(from_field)} WHERE {quote_name(pk_field)} = %s"
    )

    with schema_editor.connection.cursor() as cursor:  # type: CursorWrapper
        total_count = count_table(cursor, table_name)
        pks = fetchall_pks(cursor, table_name, pk_field, total_count, batch_size)

        batches = [pks[i : i + batch_size] for i in range(0, len(pks), batch_size)]
        total_step = len(batches)
        for step, chunk in enumerate(batches):
            logger.info("Chunk<%d/%d> is updating", step + 1, total_step)
            for pk in chunk:
                cursor.execute(statement_tmpl, [pk])
            # warning: CAN NOT call `commit` because migration is running in `atomic` block
            # schema_editor.connection.commit()


def count_table(cursor: CursorWrapper, table_name: str) -> int:
    """count the size of given table"""
    count_sql = f"SELECT count(1) as cnt FROM {table_name}"
    cursor.execute(count_sql)
    return cursor.fetchone()[0]


def fetchall_pks(cursor: CursorWrapper, table_name: str, pk_field: str, total_size: int, batch_size: int) -> List[Any]:
    init_query_sql = f"SELECT {pk_field} FROM {table_name} ORDER BY {pk_field} LIMIT {batch_size}"
    next_query_sql = (
        f"SELECT {pk_field} FROM {table_name} WHERE {pk_field} > %s ORDER BY {pk_field} LIMIT {batch_size}"
    )

    cursor.execute(init_query_sql)
    pks = flatfetchall(cursor)

    if len(pks) < batch_size:
        return pks

    for _ in range(batch_size, total_size, batch_size):
        cursor.execute(next_query_sql, [pks[-1]])
        pks.extend(flatfetchall(cursor))
    return pks


def flatfetchall(cursor: CursorWrapper) -> List[Any]:
    """Return all rows from a cursor as a flat list"""
    return [row[0] for row in cursor.fetchall()]
