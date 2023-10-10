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
"""Fixtures are utils for writing common files for app templates
"""
from django.template import Context, Engine
from unipath import Path


class BaseFixture:
    """Base class for fixture"""

    fixtures_dirname: str = ''

    def __init__(self, project_root: str, context: dict):
        """Base class for render fixtures

        :param project_root: root of rendering project
        :param context: dict of render context
        """
        self.project_root = Path(project_root)
        self.fixture_path = None
        if self.fixtures_dirname:
            self.fixture_path = Path(__file__).parent.child('fixtures', self.fixtures_dirname)

        self.context = context

    def write_tmpl(self, tpl_name, target, **options):
        """Write a file to project directory

        :param str tpl_name: The template filename, to use a relative path, self.fixture_path
          must not be None.
        :param str target: The target path to write file.
        :param options: Additional context for template rendering.
        """
        if not tpl_name.startswith('/') and not self.fixture_path:
            raise ValueError('Must set fixture_path in order to use a relative tpl_name')

        tpl_name = tpl_name if tpl_name.startswith('/') else Path(self.fixture_path, tpl_name)
        with open(tpl_name) as fp:
            content = fp.read()

        self.write_to_file(content, target, **options)

    def write_to_file(self, content, target, **options):
        with open(Path(self.project_root, target), 'w') as fp:
            fp.write(self.render_string(content, **options))

    def append_to_file(self, content, target, **options):
        with open(Path(self.project_root, target), 'a') as fp:
            fp.write(self.render_string(content, **options))

    def render_string(self, content, **options):
        context = Context(dict(self.context, **options), autoescape=False)
        template = Engine().from_string(content)
        return template.render(context)


class ProcfileFixture(BaseFixture):
    """Fixture for Profile"""

    fixtures_dirname = 'common'

    def setup(self, **options):
        self.write_tmpl('Procfile-tpl', target='Procfile', **options)
        # Double render to render variables in commands, like this:
        #
        # web: gunicorn {{ project_name }}.wsgi --log-file -
        # -->
        # web: gunicorn ng_demo.wsgi --log-file -
        #
        with open(Path(self.project_root, 'Procfile'), 'r') as fp:
            content = fp.read()
        with open(Path(self.project_root, 'Procfile'), 'w') as fp:
            fp.write(self.render_string(content))
