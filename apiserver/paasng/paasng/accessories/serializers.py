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
from builtins import object

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.utils.i18n.serializers import TranslatedCharField

from .smart_advisor import get_default_tagset
from .smart_advisor.models import DocumentaryLink


class ListAdvisedDocLinksSLZ(serializers.Serializer):
    """Serializer for list doc links"""

    plat_panel = serializers.CharField(required=True)
    limit = serializers.IntegerField(required=False, default=4)

    def validate_plat_panel(self, value):
        try:
            tag = get_default_tagset().get("plat-panel:{}".format(value))
        except ValueError:
            raise ValidationError("{} is not a valid choice of plat-panel".format(value))
        return tag


class DocumentaryLinkSLZ(serializers.ModelSerializer):

    title = TranslatedCharField()
    short_description = TranslatedCharField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['location'] = instance.format_location
        data['link'] = instance.format_location
        # 兼容部署阶段帮助文档、部署出错帮助文档、webconsole 启用帮助文档字段
        data['name'] = data['title']
        data['text'] = data['title']
        data['description'] = data['short_description']
        return data

    class Meta(object):
        model = DocumentaryLink
        fields = ['title', 'location', 'short_description']
