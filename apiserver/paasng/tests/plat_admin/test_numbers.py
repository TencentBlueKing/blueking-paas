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
import functools
from unittest import mock

import pytest

from paasng.plat_admin.numbers.app import (
    Contribution,
    DefaultAppDataBuilder,
    LegacyAppDataBuilder,
    SimpleApp,
    calculate_user_contribution_in_app,
    group_apps_by_developers,
    make_table_apps_basic_info,
    make_table_apps_grouped_by_developer,
    make_table_apps_grouped_by_developer_simple,
    print_table,
)
from tests.conftest import skip_if_legacy_not_configured
from tests.utils.helpers import create_app as helper_create_app
from tests.utils.helpers import create_legacy_application

# Create application with source obj to make tests work
create_app = functools.partial(helper_create_app, additional_modules=['sourcectl'])
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup(init_tmpls):
    pass


class TestDefaultAppDataBuilder:
    def test_normal(self):
        app = create_app(owner_username='user1')

        builder = DefaultAppDataBuilder()
        results = list(builder.get_results())
        assert len(results) == 1
        assert isinstance(results[0], SimpleApp)
        assert app.name == results[0].name

    def test_with_filter_developers(self):
        create_app(owner_username='user1')
        create_app(owner_username='user2')

        builder = DefaultAppDataBuilder()
        builder.set_filter_developers(filter_developers=['user2'])
        results = list(builder.get_results())
        assert len(results) == 1
        assert results[0].creator == 'user2'


class TestLegacyAppDataBuilder:
    def test_normal(self):
        app = create_legacy_application()

        builder = LegacyAppDataBuilder()
        results = list(builder.get_results())

        # Find app from results
        simple_app = next((simple_app for simple_app in results if simple_app.name == app.name), None)
        assert simple_app and isinstance(simple_app, SimpleApp)


@skip_if_legacy_not_configured()
class TestCalculateUserContribution:
    def test_exception(self):
        create_app(owner_username='user1')
        user, _, apps = list(group_apps_by_developers(filter_developers=['user1']))[0]
        with pytest.raises(Exception):
            _ = calculate_user_contribution_in_app(user, apps[0])

    def test_with_mock(self):
        create_app(owner_username='user1', repo_type='bk_svn')
        user, _, apps = list(group_apps_by_developers(filter_developers=['user1']))[0]
        with mock.patch("paasng.dev_resources.sourcectl.svn.client.RemoteClient") as RemoteClient:
            RemoteClient().calculate_user_contribution.return_value = dict(
                project_total_lines=0, user_total_lines=0, project_commit_nums=0, user_commit_nums=0
            )
            contribution = calculate_user_contribution_in_app(user, apps[0])
        assert isinstance(contribution, dict)
        contribution = Contribution(**contribution)
        assert contribution.project_commit_nums == 0
        assert contribution.user_commit_nums == 0
        assert contribution.project_total_lines == 0
        assert contribution.user_total_lines == 0


class TestTablesAppGroupedByDevelopers:
    def test_with_filter_developers(self):
        create_app(owner_username='user1')
        create_app(owner_username='user2')

        table = make_table_apps_grouped_by_developer(filter_developers=['user1'])
        assert len(table.rows) == 1

    def test_without_filter_developers(self):
        create_app(owner_username='user1')
        create_app(owner_username='user1')

        table = make_table_apps_grouped_by_developer()
        assert len(table.rows) == 2


class TestTablesAppGroupedByDevelopersSimple:
    def test_with_filter_developers(self):
        create_app(owner_username='user1')
        create_app(owner_username='user2')

        table = make_table_apps_grouped_by_developer_simple(filter_developers=['user1'])
        assert len(table.rows) == 1
        metadata = table.metadata
        assert metadata['users_cnt_total'] == 1
        assert metadata['users_cnt_created'] == 1
        assert metadata['users_cnt_developed'] == 1


class TestTablesAppBasicInfo:
    def test_with_matched(self):
        app = create_app(owner_username='user1')
        legacy_app = create_legacy_application()
        # Create another legacy app which should not be included in table
        create_legacy_application()

        table = make_table_apps_basic_info(filter_app_codes=[app.code, legacy_app.code])
        assert len(table.rows) == 2

    def test_without_matched(self):
        create_app(owner_username='user1')
        table = make_table_apps_basic_info(filter_app_codes=['invalid-code'])
        assert len(table.rows) == 0


def test_print_table():
    create_app(owner_username='user1')
    create_app(owner_username='user1')

    table = make_table_apps_grouped_by_developer()
    with open('/dev/null', 'w') as fp:
        print_table(table, stream=fp)
