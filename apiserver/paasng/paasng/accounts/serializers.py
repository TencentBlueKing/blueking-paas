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
from rest_framework import serializers

from paasng.utils.serializers import UserField, VerificationCodeField

from .constants import AccountFeatureFlag


class UserSLZ(serializers.Serializer):
    email = serializers.EmailField(help_text=u"邮箱地址")
    chinese_name = serializers.CharField(help_text=u"中文名称")
    avatar_url = serializers.CharField(help_text=u"头像地址")
    bkpaas_user_id = serializers.CharField(help_text=u"蓝鲸用户ID")
    phone = serializers.CharField(help_text=u"手机号码")
    username = serializers.CharField(help_text=u"用户名，内部版是rtx")


class VerificationCodeSLZ(serializers.Serializer):
    verification_code = VerificationCodeField()


class AccountFeatureFlagSLZ(serializers.Serializer):
    user = UserField()
    feature = serializers.ChoiceField(choices=AccountFeatureFlag.get_choices(), help_text="特性名称", source="name")
    isEffect = serializers.BooleanField(source="effect")


class BackendDisplayInfoSLZ(serializers.Serializer):
    icon = serializers.URLField(allow_null=True, help_text="icon")
    display_name = serializers.CharField(allow_null=True, help_text="可读性高的名称")
    address = serializers.URLField(allow_null=True, help_text="第三方平台地址")
    description = serializers.CharField(allow_null=True)
    auth_docs = serializers.CharField(allow_null=True, help_text="授权指引文档")


class BackendDisplayPropertiesSLZ(serializers.Serializer):
    always_show_associated_panel = serializers.BooleanField(default=False, help_text="是否需要默认展示授权框")


class TokenHolderSLZ(serializers.Serializer):
    id = serializers.IntegerField(help_text="资源id", default=None)
    scope = serializers.CharField(default=None, source="get_scope")
    provider = serializers.CharField(help_text="backend名称")


class OauthBackendInfoSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="backend名称")
    auth_url = serializers.CharField(help_text="Oauth授权地址")
    display_info = BackendDisplayInfoSLZ()
    display_properties = BackendDisplayPropertiesSLZ(help_text="额外的展示属性")
    token_list = TokenHolderSLZ(many=True)


class OAuthRefreshTokenSLZ(serializers.Serializer):
    refresh_token = serializers.CharField(help_text="refresh_token")
