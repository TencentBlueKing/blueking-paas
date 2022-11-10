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


class TagAdmin(admin.ModelAdmin):
    search_fields = list_filter = ["instance", "key", "value"]
    list_display = ["id"] + list_filter


class ClusterAdmin(admin.ModelAdmin):
    search_fields = ["name", "host"]
    list_filter = ["version", "enable"]
    list_display = ["id", "name", "host", "version", "enable"]


admin.site.register(models.Cluster, ClusterAdmin)
admin.site.register(models.ClusterTag, TagAdmin)


class UserPolicyAdmin(admin.ModelAdmin):
    search_fields = ["name", "definitions"]
    list_filter = ["apply_to", "enable"]
    list_display = ["id", "name", "pattern", "apply_to", "priority", "enable", "link_type", "linked"]


admin.site.register(models.UserPolicy, UserPolicyAdmin)
admin.site.register(models.UserPolicyTag, TagAdmin)


class LimitPolicyAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = ["limit", "enable"]
    list_display = ["id", "name", "limit", "value", "enable", "link_type", "linked"]


admin.site.register(models.LimitPolicy, LimitPolicyAdmin)
admin.site.register(models.LimitPolicyTag, TagAdmin)


class InstanceBillAdmin(admin.ModelAdmin):
    search_fields = ["name", "action"]
    list_filter = ["action"]
    list_display = ["uuid", "name", "action", "created", "updated"]


admin.site.register(models.InstanceBill, InstanceBillAdmin)
