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

import fnmatch
import logging
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Dict, List

from jinja2.defaults import VARIABLE_END_STRING, VARIABLE_START_STRING

from paasng.platform.templates.constants import RenderMethod
from paasng.utils import safe_jinja2

logger = logging.getLogger(__name__)


class EnhancedTemplateCommand:
    """Enhanced TemplateCommand, based on django's default one

    - Only render files endswith "-tpl" suffix
    - Use extra after hooks to remove bad files and rename rendered files back to normal

    :param render_method: Render method (Only support DjangoTemplate, Jinja2ForGolang)
    :param force_executable_files: Always make these files executable
    """

    IGNORE_PATTERNS = ("*.pyc", "*.pyo", "CVS", "tmp", ".git", ".svn")
    default_options: Dict[str, Any] = {}

    def __init__(self, render_method: RenderMethod, force_executable_files: List | None = None):
        # 渲染方式检查（注意：DjangoTemplate 其实也是通过 Jinja2 渲染的）
        if render_method not in [RenderMethod.DJANGO_TEMPLATE, RenderMethod.JINJA2_DOUBLE_SQUARE_BRACKET]:
            raise ValueError(f"Invalid render method: {render_method}")

        self.render_method = render_method

        # 强制设置为可执行的文件
        if force_executable_files is None:
            force_executable_files = []

        self.force_executable_files = set(force_executable_files)

    def handle(self, target: str, template: str, context: Dict[str, str]):
        """Render templates to files"""
        if not Path(template).is_absolute():
            raise ValueError("template path must be absolute!")

        for root, dirs, all_files in os.walk(template, followlinks=False):
            # Ignore dirs and files which should be ignored
            # See: https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]
            files = [f for f in all_files if not self._should_ignore(f)]

            rel_path = root[len(template) :].lstrip("/")
            dst_path = Path(os.path.join(target, rel_path))
            dst_path.mkdir(exist_ok=True)
            for filename in files:
                src_file = Path(root) / filename
                # Ignore symbolic links
                if os.path.islink(src_file):
                    continue

                dst_file = dst_path / filename
                if filename.endswith("-tpl"):
                    dst_file = Path(str(dst_file)[: -len("-tpl")])
                    with open(dst_file, "w", encoding="utf-8") as f:
                        f.write(self._render(src_file, context))
                else:
                    shutil.copyfile(src_file, dst_file, follow_symlinks=False)

                # Make file executable
                rel_dst_filename = str(dst_file)[len(target) :].lstrip("/")
                if str(rel_dst_filename) in self.force_executable_files:
                    logger.debug(f"File {rel_dst_filename} should be executable, change its attributes")
                    st = dst_file.stat()
                    os.chmod(dst_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _should_ignore(self, name: str) -> bool:
        """Should ignore this file/directory or not"""
        return any(fnmatch.fnmatch(name, p) for p in self.IGNORE_PATTERNS)

    def _render(self, filepath: Path, context: Dict[str, str]) -> str:
        with open(filepath, "r", encoding="utf-8", errors="strict") as f:
            source = f.read()

        var_start_str, var_end_str = VARIABLE_START_STRING, VARIABLE_END_STRING
        # Golang 模板中默认使用 {{ 和 }}，因此按约定需要由开发者中心渲染的部分应使用 [[ 和 ]]
        if self.render_method == RenderMethod.JINJA2_DOUBLE_SQUARE_BRACKET:
            var_start_str, var_end_str = "[[", "]]"

        return safe_jinja2.Template(
            source,
            # 设置变量匹配的前后字符串
            variable_start_string=var_start_str,
            variable_end_string=var_end_str,
            # 保留文件末尾的空行
            keep_trailing_newline=True,
        ).render(context)
