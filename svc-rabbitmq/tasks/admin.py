# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from django.contrib import admin

from . import models


class CronTaskAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = ["enabled", "last_run_time", "next_run_time"]
    list_display = ["id", "name", "interval", "next_run_time", "last_run_time", "enabled"]
    readonly_fields = ["last_run_time", "callable", "get_result", "pre_call", "post_call"]
    fieldsets = [
        [None, {"fields": ["name", "interval", "enabled", "next_run_time"]}],
        ["Information", {"fields": ["last_run_time", "callable", "get_result", "pre_call", "post_call"]}],
    ]


admin.site.register(models.CronTask, CronTaskAdmin)
