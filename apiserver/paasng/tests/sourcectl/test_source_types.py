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
from typing import TYPE_CHECKING, Type, cast

import pytest

from paasng.accounts.oauth.backends import OAuth2Backend
from paasng.dev_resources.sourcectl.source_types import ServerConfig, SourcectlTypeNames, SourceTypes, SourceTypeSpec
from paasng.platform.modules.constants import SourceOrigin

if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.connector import ModuleRepoConnector  # noqa


@pytest.fixture
def server_config_with_region():
    return {
        '_lookup_field': 'region',
        'data': {'r1': {'url': 'r1.com'}, 'r2': {'url': 'r2.com'}},
    }


@pytest.fixture
def oauth_credentials():
    return {
        "authorization_base_url": "https://example.com",
        "client_id": "foo",
        "client_secret": "bar",
        "token_base_url": "https://example.com",
    }


@pytest.fixture
def oauth_display_info():
    return {
        "display_name": "dummy-oauth",
        "address": "dummy-address",
        "description": "dummy-description",
        "auth_docs": "dummy-auth-docs",
        "icon": "",
    }


@pytest.fixture
def partial_oauth_display_info():
    return {"display_name": "dummy-override"}


class TestServerConfig:
    def test_region(self, server_config_with_region):
        config = ServerConfig(server_config_with_region)
        assert config.get('r1') == {'url': 'r1.com'}
        assert config.get('r2') == {'url': 'r2.com'}

    def test_region_not_found_default(self, server_config_with_region):
        config = ServerConfig(server_config_with_region)
        assert config.get('r100', use_default_value=True) is not None

    def test_region_agonostic_error(self, server_config_with_region):
        config = ServerConfig(server_config_with_region)
        with pytest.raises(TypeError):
            config.get_region_agnostic()

    def test_region_agonostic_normal(self, server_config_with_region):
        config = ServerConfig({'foo': 'bar'})
        assert config.get_region_agnostic() == {'foo': 'bar'}


class DummyClass:
    pass


class DummyOAuth2Backend(OAuth2Backend):
    _default_display_info = {"display_name": "dummy-name", "description": "dummy-description"}


class DummySourceTypeSpec(SourceTypeSpec):
    connector_class = cast(Type['ModuleRepoConnector'], DummyClass)
    repo_controller_class = DummyClass  # type: ignore
    oauth_backend_class = DummyOAuth2Backend
    basic_type = 'svn'

    _default_source_origin = SourceOrigin.AUTHORIZED_VCS
    _default_label = 'dummy'
    _default_display_info = {
        'name': 'dummy',
        'description': 'dummy',
    }


class GitDummySourceTypeSpec(SourceTypeSpec):
    connector_class = cast(Type['ModuleRepoConnector'], DummyClass)
    repo_controller_class = DummyClass  # type: ignore
    oauth_backend_class = DummyOAuth2Backend
    basic_type = 'git'

    _default_source_origin = SourceOrigin.AUTHORIZED_VCS
    _default_label = 'dummy'
    _default_display_info = {
        'name': 'dummy',
        'description': 'dummy',
    }


class TestSourceTypeSpec:
    def test_normal(self, server_config_with_region):
        spec = DummySourceTypeSpec('my_dummy', server_config=server_config_with_region)
        assert spec.make_feature_flag_field().name == 'ENABLE_MY_DUMMY'
        assert spec.support_oauth() is True
        assert spec.get_server_config('r1') == {'url': 'r1.com'}

    def test_non_region_server_config(self):
        spec = DummySourceTypeSpec('my_dummy', server_config={'foo': 'bar'})
        assert spec.get_server_config('r1') == {'foo': 'bar'}

    def test_oauth_credentials(self, server_config_with_region, oauth_credentials):
        """测试只使用 oauth_credentials 配置 credentials, display_info 使用类中的默认值"""
        spec = DummySourceTypeSpec(
            'my_dummy', server_config=server_config_with_region, oauth_credentials=oauth_credentials
        )
        backend = spec.make_oauth_backend()
        assert backend
        assert backend.authorization_base_url == oauth_credentials["authorization_base_url"]
        assert backend.client_id == oauth_credentials["client_id"]
        assert backend.client_secret == oauth_credentials["client_secret"]
        assert backend.token_base_url == oauth_credentials["token_base_url"]
        assert backend.display_info.display_name == "dummy-name"
        assert backend.display_info.description == "dummy-description"

    def test_oauth_backend_config(self, server_config_with_region, oauth_credentials, oauth_display_info):
        """测试只使用 oauth_backend_config 完成 credentials 和 display_info"""
        merged = {"display_info": oauth_display_info, **oauth_credentials}
        spec = DummySourceTypeSpec('my_dummy', server_config=server_config_with_region, oauth_backend_config=merged)
        backend = spec.make_oauth_backend()
        assert backend
        assert backend.authorization_base_url == merged["authorization_base_url"]
        assert backend.client_id == merged["client_id"]
        assert backend.client_secret == merged["client_secret"]
        assert backend.token_base_url == merged["token_base_url"]
        assert backend.display_info.to_dict() == merged["display_info"]

    def test_oauth_mixin(self, server_config_with_region, oauth_credentials, oauth_display_info):
        """测试使用 oauth_credentials 配置 credentials, oauth_backend_config 配置 display_info"""
        spec = DummySourceTypeSpec(
            'my_dummy',
            server_config=server_config_with_region,
            oauth_backend_config={"display_info": oauth_display_info},
            oauth_credentials=oauth_credentials,
        )
        backend = spec.make_oauth_backend()
        assert backend
        assert backend.authorization_base_url == oauth_credentials["authorization_base_url"]
        assert backend.client_id == oauth_credentials["client_id"]
        assert backend.client_secret == oauth_credentials["client_secret"]
        assert backend.token_base_url == oauth_credentials["token_base_url"]
        assert backend.display_info.to_dict() == oauth_display_info

    def test_partial_overwrite_display_info(
        self, server_config_with_region, oauth_credentials, partial_oauth_display_info
    ):
        """测试只覆盖 display_info 部分值"""
        merged = {"display_info": partial_oauth_display_info, **oauth_credentials}
        spec = DummySourceTypeSpec('my_dummy', server_config=server_config_with_region, oauth_backend_config=merged)
        backend = spec.make_oauth_backend()
        assert backend
        assert backend.display_info.display_name == partial_oauth_display_info["display_name"]
        assert backend.display_info.description == "dummy-description"


class TestSourceTypes:
    @pytest.fixture
    def source_types(self):
        source_type_spec_configs = [
            {
                'spec_cls': 'tests.sourcectl.test_source_types.DummySourceTypeSpec',
                'attrs': {'name': 'my_dummy_1', 'label': 'Dummy-1'},
            },
            {
                'spec_cls': 'tests.sourcectl.test_source_types.GitDummySourceTypeSpec',
                'attrs': {'name': 'my_dummy_2'},
            },
        ]
        obj = SourceTypes()
        obj.load_from_configs(source_type_spec_configs)
        return obj

    def test_items(self, source_types):
        assert len(source_types.data) == 2
        assert len(source_types.items()) == 2

    def test_get_by_name(self, source_types):
        assert source_types.get('my_dummy_1') is not None

    def test_find_by_type(self, source_types):
        assert source_types.find_by_type(DummySourceTypeSpec) is not None
        with pytest.raises(ValueError):
            source_types.find_by_type(int)

    def test_get_choices(self, source_types):
        assert source_types.get_choices() == [
            ('my_dummy_1', 'Dummy-1'),
            ('my_dummy_2', 'dummy'),
        ]

    def test_get_choice_label(self, source_types):
        assert source_types.get_choice_label('my_dummy_1') == 'Dummy-1'


class TestSourceTypeNames:
    @pytest.fixture
    def source_types(self):
        source_type_spec_configs = [
            {
                'spec_cls': 'tests.sourcectl.test_source_types.DummySourceTypeSpec',
                'attrs': {'name': 'my_dummy_1'},
            },
            {
                'spec_cls': 'tests.sourcectl.test_source_types.DummySourceTypeSpec',
                'attrs': {'name': 'my_dummy_2'},
            },
            {
                'spec_cls': 'tests.sourcectl.test_source_types.GitDummySourceTypeSpec',
                'attrs': {'name': 'my_another_dummy'},
            },
        ]
        obj = SourceTypes()
        obj.load_from_configs(source_type_spec_configs)
        return obj

    @pytest.mark.parametrize(
        'key,result,exc_raised',
        [
            ('my_dummy_1', 'my_dummy_1', False),
            ('GitDummySourceTypeSpec', 'my_another_dummy', False),
            ('GitDummy', 'my_another_dummy', False),
            ('git_dummy', 'my_another_dummy', False),
            ('DummySourceTypeSpec', None, True),
            ('dummy', None, True),
            ('invalid_name', None, True),
        ],
    )
    def test_get(self, key, result, exc_raised, source_types):
        names = SourcectlTypeNames(source_types)
        if exc_raised:
            with pytest.raises(KeyError):
                names.get(key)
            return

        assert names.get(key) == result

    def test_default(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names.get_default() == 'my_dummy_1'

    def test_build_name_index(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names._build_name_index() == {
            'my_dummy_1': ['my_dummy_1'],
            'my_dummy_2': ['my_dummy_2'],
            'my_another_dummy': ['my_another_dummy'],
        }

    def test_build_type_name_index(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names._build_type_name_index() == {
            'DummySourceTypeSpec': ['my_dummy_1', 'my_dummy_2'],
            'GitDummySourceTypeSpec': ['my_another_dummy'],
        }

    def test_build_shorter_type_name_index(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names._build_shorter_type_name_index() == {
            'Dummy': ['my_dummy_1', 'my_dummy_2'],
            'dummy': ['my_dummy_1', 'my_dummy_2'],
            'GitDummy': ['my_another_dummy'],
            'git_dummy': ['my_another_dummy'],
        }

    def test_getattr(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names.git_dummy == 'my_another_dummy'

    @pytest.mark.parametrize(
        'basic_type,expected_names',
        [
            ('svn', ['my_dummy_1', 'my_dummy_2']),
            ('git', ['my_another_dummy']),
        ],
    )
    def test_filter_by_basic_type(self, basic_type, expected_names, source_types):
        names = SourcectlTypeNames(source_types)
        assert names.filter_by_basic_type(basic_type) == expected_names

    def test_validate_svn(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names.validate_svn('my_dummy_1') is True
        assert names.validate_svn('my_another_dummy') is False

    def test_validate_git(self, source_types):
        names = SourcectlTypeNames(source_types)
        assert names.validate_git('my_dummy_1') is False
        assert names.validate_git('my_another_dummy') is True
