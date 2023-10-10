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
import logging

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db.transaction import atomic
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import AccountFeatureFlag, User, UserPrivateToken, UserProfile
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.infras.accounts.serializers import AccountFeatureFlagSLZ
from paasng.plat_admin.admin42.serializers import accountmgr
from paasng.plat_admin.admin42.utils.filters import UserProfileFilterBackend
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.core.region.models import get_all_regions

logger = logging.getLogger(__name__)


class UserProfilesManageView(GenericTemplateView):
    name = "用户列表"
    queryset = UserProfile.objects.exclude(role=SiteRole.USER.value).order_by('role', '-created')
    serializer_class = accountmgr.UserProfileSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/accountmgr/user_profile_list.html"
    filter_backends = [UserProfileFilterBackend]

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["user_profile_list"] = self.list(self.request, *self.args, **self.kwargs)
        kwargs['pagination'] = self.get_pagination_context(self.request)
        kwargs["SITE_ROLE"] = dict(SiteRole.get_choices())
        kwargs["PROVIDER_TYPE"] = dict(accountmgr.PROVIDER_TYPE_CHCOISE)
        kwargs["ALL_REGIONS"] = list(get_all_regions())
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserProfilesManageViewSet(viewsets.GenericViewSet):
    serializer_class = accountmgr.UserProfileSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    @atomic
    def bulk_create(self, request):
        serializer = accountmgr.UserProfileBulkCreateFormSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider_type = ProviderType(serializer.validated_data["provider_type"])
        role = serializer.validated_data["role"]
        enable_regions = ";".join(serializer.validated_data["enable_regions"])

        if provider_type not in [ProviderType.DATABASE, settings.USER_TYPE]:
            raise NotImplementedError(f"不支持创建ProviderType类型为 {provider_type} 的用户")

        results = []
        for username in serializer.data['username_list']:
            if provider_type is ProviderType.DATABASE:
                # 创建平台系统用户
                user, created = User.objects.get_or_create(username=username)
                if created:
                    UserPrivateToken.objects.create_token(user=user, expires_in=None)

            user_id = user_id_encoder.encode(provider_type, username)
            obj, _ = UserProfile.objects.update_or_create(
                user=user_id, defaults={'role': role, 'enable_regions': enable_regions}
            )
            obj.refresh_from_db(fields=["role", "enable_regions"])
            results.append(obj)
        return Response(self.get_serializer(results, many=True).data)

    def list(self, request):
        queryset = UserProfile.objects.order_by('role', '-created')
        queryset = UserProfileFilterBackend().filter_queryset(request, queryset, self)
        return Response(self.get_serializer(self.paginate_queryset(queryset), many=True).data)

    def update(self, request):
        slz = accountmgr.UserProfileUpdateFormSLZ(
            data=dict(
                user=dict(username=request.data["username"], provider_type=request.data["provider_type"]),
                **request.data,
            )
        )
        slz.is_valid(True)
        data = slz.validated_data

        user_id = data["user"]
        profile = UserProfile.objects.get(user=user_id)
        profile.role = data['role']
        profile.enable_regions = ";".join(data["enable_regions"])
        profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request):
        provider_type = int(request.query_params["provider_type"])
        user_id = user_id_encoder.encode(ProviderType(provider_type).value, request.query_params["username"])
        profile = UserProfile.objects.get(user=user_id)
        # profile.role = SiteRole.NOBODY.value
        profile.role = SiteRole.BANNED_USER.value
        profile.save()
        return Response(self.get_serializer(profile).data, status=status.HTTP_204_NO_CONTENT)


class AccountFeatureFlagManageView(GenericTemplateView):
    template_name = "admin42/accountmgr/account_feature_flags.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "用户特性管理"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["ACCOUNT_FEATUREFLAG_CHOICES"] = dict(AFF.get_choices())
        kwargs["feature_flag_list"] = AccountFeatureFlagSLZ(AccountFeatureFlag.objects.all(), many=True).data
        return kwargs


class AccountFeatureFlagManageViewSet(viewsets.GenericViewSet):
    schema = None
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request):
        return Response(AccountFeatureFlagSLZ(AccountFeatureFlag.objects.all(), many=True).data)

    def update_or_create(self, request):
        slz = AccountFeatureFlagSLZ(data=dict(user=dict(username=request.data["username"]), **request.data))
        slz.is_valid(True)
        data = slz.validated_data

        AccountFeatureFlag.objects.set_feature(get_user_by_user_id(data["user"]), data["name"], data["effect"])
        return Response(status=status.HTTP_204_NO_CONTENT)
