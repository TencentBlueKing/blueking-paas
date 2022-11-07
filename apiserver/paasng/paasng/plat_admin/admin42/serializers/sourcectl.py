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
from typing import Dict

from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.dev_resources.sourcectl.models import SourceTypeSpecConfig


class SourceTypeSpecConfigSLZ(serializers.ModelSerializer):
    class Meta:
        model = SourceTypeSpecConfig
        fields = '__all__'

    def validate_server_config(self, conf: Dict) -> Dict:
        if type(conf) != dict:
            raise ValidationError(_('服务配置格式必须为 Dict'))
        return conf

    def validate_display_info_zh_cn(self, display_info: Dict) -> Dict:
        return self._validate_display_info(display_info)

    def validate_display_info_en(self, display_info: Dict) -> Dict:
        return self._validate_display_info(display_info)

    def validate_oauth_display_info_zh_cn(self, display_info: Dict) -> Dict:
        return self._validate_oauth_display_info(display_info)

    def validate_oauth_display_info_en(self, display_info: Dict) -> Dict:
        return self._validate_oauth_display_info(display_info)

    def validate(self, attrs: Dict) -> Dict:
        # 尝试使用配置初始化 SourceTypeSpec 以校验配置的合法性
        conf = SourceTypeSpecConfig(**attrs).to_dict()
        try:
            cls = import_string(attrs['spec_cls'])
        except ImportError:
            raise ValidationError(_('配置类路径有误，导入失败'))

        try:
            source_type_spec = cls(**conf['attrs'])
        except Exception as e:
            raise ValidationError(_('初始化 SourceTypeSpec 失败：{}').format(str(e)))

        if not source_type_spec.support_oauth():
            return attrs

        # 如果使用了支持 OAuth 配置的配置类，则必须填写相关字段
        oauth_fields_map = {
            'authorization_base_url': _('OAuth 授权链接'),
            'client_id': 'ClientID',
            'client_secret': 'ClientSecret',
            'redirect_uri': _('回调地址'),
            'token_base_url': _('获取 Token 链接'),
            'oauth_display_info_en': _('OAuth 展示信息（英）'),
            'oauth_display_info_zh_cn': _('OAuth 展示信息（中）'),
        }
        for field, title in oauth_fields_map.items():
            if not attrs.get(field):
                raise ValidationError(_('使用配置类 {} 时，字段 {} 不可为空').format(cls.__name__, title))

        return attrs

    @staticmethod
    def _validate_display_info(display_info: Dict) -> Dict:
        if type(display_info) != dict:
            raise ValidationError(_('展示信息格式必须为 Dict'))

        # 如果填写 display_info，则必须包含键 name，description
        if display_info and not ('name' in display_info and 'description' in display_info):
            raise ValidationError(_('展示信息有误，非空则必须包含 name，description 键'))

        available_fields = {'name', 'description'}
        if unsupported_fields := display_info.keys() - available_fields:
            raise ValidationError(_('展示信息不支持字段 {}').format(unsupported_fields))

        return display_info

    @staticmethod
    def _validate_oauth_display_info(display_info: Dict) -> Dict:
        if type(display_info) != dict:
            raise ValidationError(_('OAuth 展示信息格式必须为 Dict'))

        available_fields = {'icon', 'display_name', 'address', 'description', 'auth_docs'}
        if unsupported_fields := display_info.keys() - available_fields:
            raise ValidationError(_('OAuth 展示信息不支持字段 {}').format(unsupported_fields))

        return display_info
