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

from typing import Any, TypeVar

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum

T = TypeVar("T")


class OmittedType:
    def __repr__(self) -> str:
        return "OmittedType"

    def __bool__(self) -> bool:
        return False

    def __copy__(self: T) -> T:
        return self

    def __deepcopy__(self: T, _: Any) -> T:
        return self

    def dict(self, *args, **kwargs):
        raise NotImplementedError


# Sentinel value for omitted fields
OMITTED_VALUE = OmittedType()


class AppSpecVersion(IntStructuredEnum):
    # VER_1 meaning app.yaml is provided by legacy S-Mart App,
    # **this version is not supported anymore**
    VER_1 = 1

    VER_2 = 2
    # VER_3 means cnative app
    VER_3 = 3

    # UNSPECIFIED means the version is not specified
    UNSPECIFIED = -1


class AppDescPluginType(StrStructuredEnum):
    APP_VERSION = EnumField("app_version", label="应用版本")


class DiffType(StrStructuredEnum):
    ADDED = EnumField("added", label="新增")
    DELETED = EnumField("deleted", label="删除")
    NOT_MODIFIED = EnumField("not_modified", label="未改动")


WEB_PROCESS = """gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"' --timeout 600"""
CELERY_PROCESS = "python manage.py celery worker -l info --autoscale=8,1"
CELERY_PROCESS_WITH_GEVENT = "python manage.py celery worker -l info --without-gossip -P gevent -c 20"
CELERY_BEAT_PROCESS = "python manage.py celery beat"
