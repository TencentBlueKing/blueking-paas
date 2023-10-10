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
from dataclasses import asdict
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.smart_advisor import AppPLTag, AppSDKTag, PlatPanelTag
from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.models import DocumentaryLink
from paasng.accessories.smart_advisor.utils import DeploymentFailureHint, get_failure_hint
from tests.paasng.platform.engine.setup_utils import create_fake_deployment

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


class TestDocumentaryLinkAdvisor:
    def setup_data(self):
        G(DocumentaryLink, title_zh_cn="common_new_app_tutorial", affinity_tags=["plat-panel:app_created"])
        G(
            DocumentaryLink,
            title_zh_cn="py_new_app_tutorial",
            affinity_tags=["app-pl:python", "plat-panel:app_created"],
        )
        G(
            DocumentaryLink,
            title_zh_cn="golang_new_app_tutorial",
            affinity_tags=["app-pl:go", "plat-panel:app_created"],
        )

        G(
            DocumentaryLink,
            title_zh_cn="what_is_processes",
            affinity_tags=["plat-panel:app_deployment", "plat-panel:app_processes"],
        )
        G(DocumentaryLink, title_zh_cn="python_processes", affinity_tags=["app-pl:python", "plat-panel:app_processes"])
        G(
            DocumentaryLink,
            title_zh_cn="celery_processes",
            affinity_tags=["app-pl:python", "app-sdk:celery", "plat-panel:app_processes"],
        )

    @pytest.mark.parametrize(
        'tags,link_names',
        [
            # Normal match
            ([PlatPanelTag("app_processes")], ["what_is_processes", "python_processes", "celery_processes"]),
            # All tags matches
            ([AppPLTag('python'), PlatPanelTag("app_created")], ["py_new_app_tutorial", "common_new_app_tutorial"]),
            # Part of tags matches
            ([AppPLTag('nodejs'), PlatPanelTag("app_processes")], ["what_is_processes"]),
            # Subject has more tags
            (
                [AppPLTag('python'), PlatPanelTag("app_processes")],
                ["python_processes", "celery_processes", "what_is_processes"],
            ),
            (
                [AppPLTag('python'), AppSDKTag('celery'), PlatPanelTag("app_processes")],
                ["celery_processes", "python_processes", "what_is_processes"],
            ),
            (
                [AppPLTag('python'), AppSDKTag('gevent'), PlatPanelTag("app_processes")],
                ["python_processes", "what_is_processes"],
            ),
        ],
    )
    def test_search(self, tags, link_names):
        self.setup_data()

        advisor = DocumentaryLinkAdvisor()
        links = advisor.search_by_tags(tags)
        assert list(map(str, links)) == link_names


class TestDeploymentFailureHint:
    def test_render_links(self):
        hint = DeploymentFailureHint(
            matched_solutions_found=False,
            possible_reason='reason',
            helpers=[{'text': 'foo', 'link': '/link/'}, {'text': 'bar', 'link': '/foo/{module_name}/bar'}],
        )
        hint.render_links({'module_name': 'default'})
        assert hint.helpers[1]['link'] == '/foo/default/bar'


class TestGetFailureHint:
    def test_not_found_docs(self, bk_module):
        deployment = create_fake_deployment(bk_module)

        with mock.patch('paasng.accessories.smart_advisor.utils.DocumentaryLinkAdvisor') as mocked_advisor:
            mocked_advisor().search_by_tags.return_value = []
            hint = get_failure_hint(deployment)
            assert hint.matched_solutions_found is False

    def test_found_docs(self, bk_module):
        deployment = create_fake_deployment(bk_module)
        docs = [G(DocumentaryLink, title_zh_cn='解决方案1'), G(DocumentaryLink, title_zh_cn='解决方案2')]

        with mock.patch('paasng.accessories.smart_advisor.utils.DocumentaryLinkAdvisor') as mocked_advisor:
            mocked_advisor().search_by_tags.return_value = docs
            hint = get_failure_hint(deployment)
            _ = asdict(hint)
            assert hint.matched_solutions_found is True
            assert len(hint.helpers) == 2
