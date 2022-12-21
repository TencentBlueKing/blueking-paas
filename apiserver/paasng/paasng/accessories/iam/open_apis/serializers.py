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
from rest_framework import serializers

from paasng.accessories.iam.constants import ResourceType

from .constants import MethodType


class QueryResourceSLZ(serializers.Serializer):
    method = serializers.ChoiceField(choices=MethodType.get_choices())
    type = serializers.ChoiceField(choices=ResourceType.get_choices())
    filter = serializers.JSONField(default=dict)
    page = serializers.JSONField(default=dict)
