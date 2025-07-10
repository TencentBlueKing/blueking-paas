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

import os
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Union

from requests import Response
from requests.adapters import BaseAdapter

from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir


class MockAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self.fhs = {}

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        resp = Response()
        resp.request = request
        resp.status_code = 200
        if request.url in self.fhs:
            resp.raw = self.fhs[request.url]
        return resp

    def close(self):
        pass

    def register(self, url, fh):
        self.fhs[url] = fh

    def close_fh(self):
        for fh in self.fhs.values():
            fh.close()


def ensure_parent_exists(path: Path):
    if path.parent == path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def dump_contents_to_fs(
    contents: Dict[str, Union[str, bytes]] | None = None,
    symbolic_links: Dict[str, str] | None = None,
):
    """a helper to dumps contents fo file-system

    :param contents Dict[str, str]: a dict, the key is filename, and value is the content.
    :param symbolic_links: a dict, format: {link_name: target_file}.
    """
    with generate_temp_dir() as source_dir:
        if contents:
            for file_name, content in contents.items():
                target = source_dir / file_name
                ensure_parent_exists(target)

                if isinstance(content, bytes):
                    target.write_bytes(content)
                else:
                    target.write_text(content)

        if symbolic_links:
            for link_name, target_file in symbolic_links.items():
                target = source_dir / link_name
                ensure_parent_exists(target)
                target.symlink_to(target_file, target_is_directory=Path(target_file).is_dir())
        yield source_dir


def gen_tar(
    target_path,
    contents: Dict[str, Union[str, bytes]] | None = None,
    symbolic_links: Dict[str, str] | None = None,
):
    with dump_contents_to_fs(contents=contents, symbolic_links=symbolic_links) as source_dir:
        compress_directory(source_dir, target_path)


def gen_zip(
    target_path,
    contents: Dict[str, Union[str, bytes]] | None = None,
    symbolic_links: Dict[str, str] | None = None,
):
    with (
        dump_contents_to_fs(contents=contents, symbolic_links=symbolic_links) as source_dir,
        zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zip_file,
    ):
        # NOTE: Below code is written by Claude, use with caution
        for root, dirnames, files in os.walk(source_dir):
            for name in dirnames + files:
                file_path = Path(root) / name
                arcname = file_path.relative_to(source_dir)
                # Add symlinks
                if file_path.is_symlink():
                    # Create a symbolic link entry in the zip
                    info = zipfile.ZipInfo(str(arcname))
                    info.create_system = 3  # Unix
                    info.external_attr = 0o120755 << 16  # symlink file type + permissions
                    zip_file.writestr(info, str(file_path.readlink()))
                # Add files and directories
                else:
                    zip_file.write(file_path, arcname)


# This version of app description has been deprecated and is not supported anymore
V1_APP_DESC_EXAMPLE: dict = {
    "app_name": "foo",
    "app_code": "foo",
    "author": "blueking",
    "introduction": "blueking app",
    "is_use_celery": False,
    "version": "0.0.1",
    "env": [],
}

V2_APP_DESC_EXAMPLE: dict = {
    "spec_version": 2,
    "app_version": "0.0.1",
    "app": {
        "bk_app_code": "foo",
        "bk_app_name": "foo",
        "market": {"introduction": "foobar"},
    },
    "modules": {"default": {"is_default": True, "language": "python"}},
}
