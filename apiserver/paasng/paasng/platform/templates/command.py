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
import fnmatch
import logging
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.template import Context, Template

logger = logging.getLogger(__name__)


class EnhancedTemplateCommand:
    """Enhanced TemplateCommand, based on django's default one

    - Only render files endswith "-tpl" suffix
    - Use extra after hooks to remove bad files and rename rendered files back to normal

    :param force_executable_files: Always make these files executable
    """

    IGNORE_PATTERNS = ("*.pyc", "*.pyo", "CVS", "tmp", ".git", ".svn")
    default_options: Dict[str, Any] = {}

    def __init__(self, force_executable_files: Optional[List] = None):
        if force_executable_files is None:
            force_executable_files = []
        self.force_executable_files = set(force_executable_files)

    def should_ignore(self, name) -> bool:
        """Should ignore this file/directory or not"""
        return any(fnmatch.fnmatch(name, p) for p in self.IGNORE_PATTERNS)

    def render(self, filename, context) -> str:
        with open(filename, "r", encoding="utf-8", errors="strict") as f:
            source = f.read()
        return Template(source).render(context)

    def handle(self, target: str, template: str, **options):
        """Render templates to files"""
        if not Path(template).is_absolute():
            raise ValueError("template path must be absolute!")

        context = Context({**self.default_options, **options}, autoescape=False)
        for root, dirs, files in os.walk(template, followlinks=False):
            # Ignore dirs and files which should be ignored
            # See: https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
            dirs[:] = [d for d in dirs if not self.should_ignore(d)]
            files = [f for f in files if not self.should_ignore(f)]

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
                        f.write(self.render(src_file, context))
                else:
                    shutil.copyfile(src_file, dst_file, follow_symlinks=False)

                # Make file executable
                rel_dst_filename = str(dst_file)[len(target) :].lstrip("/")
                if str(rel_dst_filename) in self.force_executable_files:
                    logger.debug(f"File {rel_dst_filename} should be executable, change its attributes")
                    st = dst_file.stat()
                    os.chmod(dst_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
