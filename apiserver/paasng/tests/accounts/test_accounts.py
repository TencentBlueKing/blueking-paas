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
import pytest
from django.conf import settings
from django.test import TestCase
from django_dynamic_fixture import G

from paasng.accounts.permissions.application import application_resource
from paasng.accounts.permissions.tools import user_has_perm
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership
from tests.utils.auth import create_user


class TestPermissions(TestCase):
    def setUp(self):
        self.user = create_user()
        self.another_user = create_user(username='another_user')
        self.app1 = G(
            Application, owner=self.user.pk, code='awesome-app', language='Python', region=settings.DEFAULT_REGION_NAME
        )
        self.app2 = G(
            Application, owner=self.user.pk, code='fta-solution', language='PHP', region=settings.DEFAULT_REGION_NAME
        )
        self.app_another1 = G(
            Application,
            owner=self.another_user.pk,
            code='awesome-bk',
            language='PHP',
            region=settings.DEFAULT_REGION_NAME,
        )
        self.app_another2 = G(
            Application,
            owner=self.another_user.pk,
            code='gcloud',
            language='Python',
            region=settings.DEFAULT_REGION_NAME,
        )
        self.app_another3 = G(
            Application,
            owner=self.another_user.pk,
            code='awesome-php',
            language='PHP',
            region=settings.DEFAULT_REGION_NAME,
        )
        # Add self.user as a collaborator of self.app_another1
        G(
            ApplicationMembership,
            application=self.app1,
            user=self.user.pk,
            role=ApplicationRole.ADMINISTRATOR.value,
            region=settings.DEFAULT_REGION_NAME,
        )
        G(
            ApplicationMembership,
            application=self.app_another2,
            user=self.user.pk,
            role=ApplicationRole.DEVELOPER.value,
            region=settings.DEFAULT_REGION_NAME,
        )

    def test_normal(self):
        assert application_resource.get_role('administrator').has_perm('view_application') is True
        assert application_resource.get_role('developer').has_perm('view_application') is True

        assert application_resource.get_role('administrator').has_perm('manage_members') is True
        assert application_resource.get_role('developer').has_perm('manage_members') is False

    def test_application_resource(self):
        assert application_resource._get_role_of_user(self.user, self.app1) == 'administrator'
        assert application_resource._get_role_of_user(self.user, self.app_another1) == 'nobody'
        assert application_resource._get_role_of_user(self.user, self.app_another2) == 'developer'

    def test_user_has_perm_normal(self):
        assert user_has_perm(self.user, 'view_logs', self.app1) is True
        assert user_has_perm(self.user, 'view_logs', self.app_another1) is False

        assert user_has_perm(self.user, 'view_logs', self.app_another2) is True
        assert user_has_perm(self.user, 'manage_members', self.app_another2) is False

    def test_user_has_perm_illegal_params(self):
        with pytest.raises(ValueError):
            assert user_has_perm(self.user, 'not_a_perm_name', self.app1) is True

        with pytest.raises(ValueError):
            assert user_has_perm(self.user, 'not_a_perm_name', object()) is True
