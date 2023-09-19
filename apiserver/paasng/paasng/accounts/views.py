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

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts import serializers
from paasng.accounts.models import AccountFeatureFlag, Oauth2TokenHolder, UserProfile, make_verifier
from paasng.accounts.oauth.backends import get_bkapp_oauth_backend_cls
from paasng.accounts.oauth.exceptions import BKAppOauthError
from paasng.accounts.oauth.utils import get_available_backends, get_backend
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.serializers import AllRegionSpecsSLZ, OAuthRefreshTokenSLZ
from paasng.accounts.utils import create_app_oauth_backend, get_user_avatar
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.feature_flags.constants import PlatformFeatureFlag
from paasng.platform.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.utils.error_codes import error_codes
from paasng.utils.notifier import get_notification_backend

logger = logging.getLogger(__name__)


class UserInfoViewSet(APIView):
    """
    用户信息 相关
    get: 当前登录用户信息
    - [测试地址](/api/accounts/userinfo/)
    - 注意：该资源访问路径已经由原来的 `/api/user/` 变更到 `/api/accounts/userinfo/`
    """

    serializer_class = serializers.UserSLZ

    def get(self, request, *args, **kwargs):
        user = request.user
        user_logo = get_user_avatar(user.username)
        data = {
            "chinese_name": user.chinese_name,
            "avatar_url": user.avatar_url if user.avatar_url else user_logo,
            "bkpaas_user_id": user.bkpaas_user_id,
            "username": user.username,
        }
        return Response(data)


class UserVerificationRateThrottle(UserRateThrottle):
    """生成验证码接口调用频率限制"""

    THROTTLE_RATES = {"user": "6/min"}


class UserVerificationGenerationView(APIView):
    throttle_classes = (UserVerificationRateThrottle,)

    def post(self, request):
        """
        验证码-生成并发送验证码到用户的手机
        - 注意：接口调用有频率限制 6/min
        """
        if not PlatformFeatureFlag.get_default_flags()[PlatformFeatureFlag.VERIFICATION_CODE]:
            raise error_codes.FEATURE_FLAG_DISABLED

        verifier = make_verifier(request.session, request.data.get('func'))
        noti_backend = get_notification_backend()

        message = _("您的蓝鲸验证码是：{verification_code}，请妥善保管。").format(verification_code=verifier.set_current_code())

        result = noti_backend.wecom.send([request.user.username], message, _('蓝鲸平台'))

        if not result:
            raise error_codes.ERROR_SENDING_NOTIFICATION

        return JsonResponse({}, status=status.HTTP_201_CREATED)


class UserVerificationValidationView(APIView):
    serializer_class = serializers.VerificationCodeSLZ

    def put(self, request):
        """
        验证码-测试验证码
        - 验证成功后，可以带上验证码发起最终操作
        """
        if not PlatformFeatureFlag.get_default_flags()[PlatformFeatureFlag.VERIFICATION_CODE]:
            raise error_codes.FEATURE_FLAG_DISABLED

        serializer = serializers.VerificationCodeSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data
        verifier = make_verifier(request.session)
        is_valid = verifier.validate(data["verification_code"])
        return JsonResponse({"is_valid": is_valid})


class OauthTokenViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """
    以用户身份申请 BKApp 的 AccessToken
    """

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def fetch_paasv3cli_token(self, request):
        """获取代表 paasv3cli 和用户身份的 AccessToken, 暂不考虑 refresh token"""
        backend = get_bkapp_oauth_backend_cls().from_paasv3cli()
        try:
            return Response(
                data=backend.fetch_token(
                    username=request.user.username, user_credential=backend.get_user_credential_from_request(request)
                )
            )
        except BKAppOauthError as e:
            return Response(status=e.response_code, data={"message": e.error_message})

    def fetch_app_token(self, request, app_code: str, env_name: str):
        """获取代表指定应用和用户身份的 AccessToken"""
        application = self.get_application()
        try:
            backend = create_app_oauth_backend(application, env_name=env_name)
        except BkOauthClientDoesNotExist:
            raise error_codes.CLIENT_CREDENTIALS_MISSING
        try:
            return Response(
                data=backend.fetch_token(
                    username=request.user.username, user_credential=backend.get_user_credential_from_request(request)
                )
            )
        except BKAppOauthError as e:
            return Response(status=e.response_code, data={"message": e.error_message})

    @swagger_auto_schema(request_body=OAuthRefreshTokenSLZ)
    def refresh_app_token(self, request, app_code: str, env_name: str):
        """刷新代表指定应用和用户身份的 AccessToken"""
        application = self.get_application()
        try:
            backend = create_app_oauth_backend(application, env_name=env_name)
        except BkOauthClientDoesNotExist:
            raise error_codes.CLIENT_CREDENTIALS_MISSING

        slz = OAuthRefreshTokenSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            return Response(data=backend.refresh_token(refresh_token=data["refresh_token"]))
        except BKAppOauthError as e:
            return Response(status=e.response_code, data={"message": e.error_message})

    def validate_app_token(self, request, app_code: str, env_name: str):
        application = self.get_application()
        try:
            backend = create_app_oauth_backend(application, env_name=env_name)
        except BkOauthClientDoesNotExist:
            raise error_codes.CLIENT_CREDENTIALS_MISSING

        return Response(data={"result": backend.validate_token(request.data["access_token"])})


class Oauth2BackendsViewSet(viewsets.ViewSet):
    """Oauth2 backends"""

    @staticmethod
    def get_user_from_request(request) -> UserProfile:
        return UserProfile.objects.get_profile(request.user)

    @staticmethod
    def pick_useful_params(token_info) -> dict:
        token_params = {}
        useful_fields = ["token_type", "access_token", "refresh_token", "scope"]
        for useful_field in useful_fields:
            token_params[useful_field] = token_info.get(useful_field, "")

        return token_params

    @swagger_auto_schema(responses={200: serializers.OauthBackendInfoSLZ(many=True)})
    def list(self, request):
        """mainly for showing auth link to users"""
        user_profile = self.get_user_from_request(request)

        backends_info = []
        for sourcectl_name, backend in get_available_backends():
            backend_info = dict(
                name=sourcectl_name,
                auth_url=backend.get_authorization_url(),
                display_info=backend.display_info.to_dict(),
                display_properties=dict(always_show_associated_panel=backend.supports_multi_tokens),
                token_list=user_profile.token_holder.filter(provider=sourcectl_name).filter_valid_tokens(),
            )
            backends_info.append(backend_info)

        return Response(serializers.OauthBackendInfoSLZ(backends_info, many=True).data)

    def bind(self, request, backend):
        """get access token from provider and bind to userProfile"""
        backend_name = backend
        # The name of oauth backend is identical with the name of source control type:
        #   backend_name == sourcectl_name
        user_profile = self.get_user_from_request(request)
        try:
            backend = get_backend(backend_name=backend_name)
        except ValueError:
            raise error_codes.OAUTH_UNKNOWN_BACKEND_NAME

        try:
            token_info = backend.fetch_token(redirect_url=request.build_absolute_uri())
        except Exception:
            msg = f"failed to get token from {backend}"
            logger.exception(msg)
            return Response(data={"message": msg}, status=status.HTTP_400_BAD_REQUEST)

        token_params = self.pick_useful_params(token_info)
        scope = token_params.pop("scope", None)
        try:
            Oauth2TokenHolder.objects.update_or_create(
                provider=backend_name, user=user_profile, region='ieod', scope=scope, defaults=token_params
            )
        except Exception:
            msg = f"failed to save access token(from {backend}) to {user_profile.username}"
            logger.exception(msg)
            return Response(data={"message": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return HttpResponse(b"<script>setTimeout(window.close, 2000)</script>" + _("授权成功, 2秒后自动关闭该页面").encode())

    def disconnect(self, request, backend, pk):
        """delete access token which is bind to user where pk={pk}"""
        user_profile = self.get_user_from_request(request)
        backend_name = backend
        try:
            get_backend(backend_name=backend_name)
        except ValueError:
            raise error_codes.OAUTH_UNKNOWN_BACKEND_NAME

        try:
            # assume one person only hold one access token per backend
            # Q: Why we trying to delete token holder instead of setting active to false, and
            # activate it when we need to reuse?
            # A: Because access token is volatile, we will not reuse it after disabled, so
            # it's easier to get a new one rather than reuse the old one
            Oauth2TokenHolder.objects.filter(pk=pk, provider=backend_name, user=user_profile).delete()
        except Exception:
            msg = f"failed to delete access token from {backend_name}"
            logger.exception(msg)
            return Response(data={"message": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data={"success": f"disconnect from {backend_name}"})


class AccountFeatureFlagViewSet(viewsets.ViewSet):
    @swagger_auto_schema(tags=["特性标记"])
    def list(self, request):
        flags = AccountFeatureFlag.objects.get_user_features(request.user)
        return Response(flags)


class RegionSpecsViewSet(viewsets.ViewSet):
    """ViewSet for region"""

    permission_classes = [IsAuthenticated]

    def retrieve(self, request):
        # TODO: 当前存在漏洞，如果用户没有创建某 region 应用的权限，但他又是这个 region 下应用的开发者。那么当他进入该应用后，
        # 点击创建新模块页面，访问 specs 接口时，不会返回对应 region 的相关信息（因为没权限），最终会导致前端页面报错。
        #
        # Region 的创建应用权限和管理某个 Region 下应用（创建模块）权限等没有细化。
        user_profile = UserProfile.objects.get_profile(self.request.user)
        regions = user_profile.enable_regions
        all_spec_slz = AllRegionSpecsSLZ(regions)
        return Response(all_spec_slz.serialize())
