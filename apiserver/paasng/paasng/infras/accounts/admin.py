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
from django.contrib import admin

from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    # it's very hard to search user by username which is a property of model,
    # so it is easier to search by command+f in browser when listing enough items
    # (almost 1000+ user, command+f up to 2 times)
    list_per_page = 500
    list_display = ['username', 'user', 'role', 'feature_flags', 'enable_regions']
    search_fields = ['user', 'role', 'feature_flags', 'enable_regions']


admin.site.register(UserProfile, UserProfileAdmin)
