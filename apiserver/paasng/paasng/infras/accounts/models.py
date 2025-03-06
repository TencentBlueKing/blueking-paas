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

import datetime
import random
from typing import Dict, List, Optional

from bkpaas_auth import get_user_by_user_id
from blue_krill.models.fields import EncryptField
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField

from paasng.infras.accounts.constants import FUNCTION_TYPE_MAP, SiteRole
from paasng.infras.accounts.constants import AccountFeatureFlag as AccountFeatureFlagConst
from paasng.infras.accounts.oauth.models import Project, Scope
from paasng.infras.accounts.oauth.utils import get_backend
from paasng.utils.models import AuditedModel, BkUserField, RegionListField, TimestampedModel
from paasng.utils.text import generate_token


class User(AbstractBaseUser):
    """An user model which stores users in databases, it was a simpler version of
    `django.contrib.auth.User`.

    This class is not supposed to be used directly as "request.user", you must wrap it with
    `bkpaas_auth.DatabaseUser` to make it compatible with "bkpaas_auth" module.
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        "username",
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=30, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"), default=False, help_text=_("Designates whether the user can log into this admin site.")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def natural_key(self):
        return (self.username,)


class UserPrivateTokenManager(models.Manager):
    """Custom manager for UserPrivateToken"""

    def create_token(self, user: User, expires_in: Optional[int]) -> "UserPrivateToken":
        """Create a random private token for user

        :param expires_in: after how many seconds, this token will be marked expired, None means
            never expires.
        """
        token = generate_token(length=30)
        expires_at = None
        if expires_in:
            expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)
        return self.create(user=user, token=token, expires_at=expires_at)

    def get_by_natural_key(self, user: str, token: str, **kwargs):
        return self.get(user=User.objects.get(username=user))


class UserPrivateToken(models.Model):
    """Private token can be used to authenticate an user, these tokens usually have very long
    expiration period. So they are perfect for system level communications.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = UserPrivateTokenManager()

    def has_expired(self):
        """Check if token has expired"""
        if not self.is_active:
            return True

        # empty "expired_at" field means this token will never expire
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def natural_key(self):
        return self.user, self.token


# 声明要求确保了所有 User 对象在任何 UserPrivateToken 对象之前序列化
UserPrivateToken.natural_key.dependencies = ["accounts.user"]  # type: ignore


class UserProfileManager(models.Manager):
    """Custom profile manager for user"""

    def get_profile(self, user):
        if user.pk is None or not user.pk:
            raise ValueError("Must provide a real user, not an anonymous user!")

        try:
            return self.model.objects.get(user=user.pk)
        except self.model.DoesNotExist:
            # Auto create user
            if settings.AUTO_CREATE_REGULAR_USER:
                return self.create(user=user.pk, role=SiteRole.USER.value)
            raise

    def get_by_natural_key(self, user: str):
        return self.get(user=user)


class UserProfile(TimestampedModel):
    """Profile field for user"""

    user = BkUserField(unique=True)
    role = models.IntegerField(default=SiteRole.USER.value)
    feature_flags = models.TextField(null=True, blank=True)
    enable_regions = RegionListField()

    objects = UserProfileManager()

    @property
    def username(self):
        return get_user_by_user_id(self.user, username_only=True).username

    def __str__(self):
        username = get_user_by_user_id(self.user, username_only=True).username
        return "{user}-{role}".format(user=username, role=self.role)

    def natural_key(self):
        return (self.user,)


class SessionCodeVerifier:
    """A verifier which generate a random code, and validates it later.
    Using request.session as a storage
    """

    numbers = 6

    def __init__(self, session, storage_key=None):
        self.storage = session
        self.storage_key = storage_key or "verification_code"

    def generate_code(self):
        return str(random.randint(10 ** (self.numbers - 1), 10**self.numbers - 1))

    def set_current_code(self):
        code = self.generate_code()
        self.storage[self.storage_key] = code
        return code

    def get_current_code(self):
        try:
            return self.storage[self.storage_key]
        except KeyError:
            return None

    def validate(self, code):
        return code == self.get_current_code()

    def validate_and_clean(self, code):
        ret = self.validate(code)
        self.storage.pop(self.storage_key, None)
        return ret


def make_verifier(session, func=None):
    storage_key = FUNCTION_TYPE_MAP.get(func, "verification_code")
    return SessionCodeVerifier(session, storage_key)


class Oauth2TokenHolderQS(models.QuerySet):
    def get_by_project(self, project: Project) -> "Oauth2TokenHolder":
        """根据传入的 GitProject, 获取Scope能覆盖到该 GitProject 的 Oauth2TokenHolder
        如果不存在, 则抛异常
        """
        for token_holder in self.filter(provider=project.type):
            scope = Scope.parse_from_str(token_holder.get_scope())
            if scope.cover_project(project):
                return token_holder
        raise self.model.DoesNotExist

    def filter_valid_tokens(self) -> List["Oauth2TokenHolder"]:
        """获取所有未过期的 token"""
        return [token_holder for token_holder in self.all() if not token_holder.expired]


class Oauth2TokenHolder(TimestampedModel):
    """OAuth2 Token for sourcectl"""

    provider = models.CharField(max_length=32)
    access_token = EncryptField(default="")
    token_type = models.CharField(max_length=16)
    refresh_token = EncryptField(default="")
    scope = JSONField(default=["api"])
    expire_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="token_holder")

    objects = Oauth2TokenHolderQS().as_manager()

    def refresh(self):
        # 1. get backend
        backend = get_backend(self.provider)
        # 2. call backend.refresh_token()
        token_pair = backend.refresh_token(self.refresh_token)
        self.access_token = token_pair.get("access_token")
        self.refresh_token = token_pair.get("refresh_token")
        self.save()

    @property
    def expired(self):
        # we don't have expire time now
        return False

    def get_scope(self) -> str:
        """
        获取 scope 实际内容

        Q: 为什么不直接写成 self.scope[0] ？
        A: 因为不同的 backend 对于 scope 字段有不同的格式表达，所以将这段解析逻辑放到 backend 实际更合理
        :return: str
        """
        backend = get_backend(self.provider)
        return backend.get_scope(self.scope)


class PrivateTokenHolder(AuditedModel):
    """Besides the OAuth2 token, the private token is also supported for authentication
    with external code services, such as GitLab, etc. When a user (such as a system user)
    cannot use OAuth2, the private token is a good alternative.

    Despite the name, the "private token" in this model is not related to the "UserPrivateToken"
    model.
    """

    provider = models.CharField(max_length=32)
    private_token = EncryptField(default="")
    expire_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="private_token_holder")

    objects = Oauth2TokenHolderQS().as_manager()

    def refresh(self):
        raise NotImplementedError("can't refresh private token")

    @property
    def expired(self):
        if self.expire_at:
            return self.expire_at < datetime.datetime.now()
        return False

    def get_scope(self) -> str:
        return "user:user"


class AccountFeatureFlagManager(models.Manager):
    def has_feature(self, user: User, key: AccountFeatureFlagConst) -> bool:
        """判断 user 是否具有 feature, 如无，则返回默认值"""
        try:
            effect = self.get(user=user.pk, name=AccountFeatureFlagConst(key).value).effect
        except AccountFeatureFlag.DoesNotExist:
            effect = AccountFeatureFlagConst._defaults[AccountFeatureFlagConst(key).value]  # type: ignore
        return effect

    def get_user_features(self, user) -> Dict[str, bool]:
        """获取 user 所有 feature 的状态"""
        flags = AccountFeatureFlagConst.get_default_flags()

        for feature in self.get_queryset().filter(user=user.pk):
            flags[feature.name] = feature.effect
        return flags

    def set_feature(self, user: User, key: AccountFeatureFlagConst, value: bool):
        """设置 user 某个 feature 状态"""
        return self.update_or_create(user=user.pk, name=AccountFeatureFlagConst(key).value, defaults={"effect": value})


class AccountFeatureFlag(TimestampedModel):
    """
    针对用户的特性标记
    """

    user = BkUserField()
    effect = models.BooleanField("是否允许(value)", default=True)
    name = models.CharField("特性名称(key)", max_length=64)
    objects = AccountFeatureFlagManager()


class AuthenticatedAppAsUserManager(models.Manager):
    def get_by_natural_key(self, bk_app_code: str):
        return self.get(bk_app_code=bk_app_code)


class AuthenticatedAppAsUser(TimestampedModel):
    """Store relationships which treat an authenticated(by API Gateway) app as an regular user,
    useful for calling system APIs without providing any real user credentials"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bk_app_code = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)

    objects = AuthenticatedAppAsUserManager()

    def natural_key(self):
        return (self.bk_app_code,)
