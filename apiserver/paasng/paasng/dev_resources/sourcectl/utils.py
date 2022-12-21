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
import os
import pathlib
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from typing import Callable, ContextManager, Iterator, List

logger = logging.getLogger(__name__)


def compress_directory(source_path, target_path):
    """Compress a directory using tar command"""
    # Use tar command to compress
    # Add "GZIP=-n" to disable gzip timestamp
    # see: https://serverfault.com/questions/110208/different-md5sums-for-same-tar-contents
    p = subprocess.Popen(
        f'GZIP=-n tar --exclude=.svn -czf {target_path} -C {source_path} .',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
    )
    _, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError('Unable to package source, error: %s' % stderr)


def uncompress_directory(source_path, target_path):
    """uncompress a tar file using tar command"""
    source_path = os.path.abspath(source_path)
    target_path = os.path.abspath(target_path)
    # -m, --touch                don't extract file modified time
    p = subprocess.Popen(
        f'tar -m -xf "{source_path}" -C "{target_path}"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
    )
    _, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError('Unable to unpackage source, error: %s' % stderr)


def __generate_temp_dir__(suffix=None) -> Iterator[pathlib.Path]:
    path = None
    try:
        path = pathlib.Path(tempfile.mkdtemp(suffix=suffix))
        logger.debug('Generating temp path: %s', path)
        yield path
    finally:
        if path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[pathlib.Path]] = contextmanager(__generate_temp_dir__)


def __generate_temp_file__(suffix="") -> Iterator[pathlib.Path]:
    path = None
    try:
        path = pathlib.Path(tempfile.mktemp(suffix=suffix))
        logger.debug('Generating temp path: %s', path)
        yield path
    finally:
        if path and path.exists():
            path.unlink()


generate_temp_file: Callable[..., ContextManager[pathlib.Path]] = contextmanager(__generate_temp_file__)


def get_all_intermediate_dirs(path: str) -> List[str]:
    """
    >>> get_all_intermediate_dirs("")
    ['']
    >>> get_all_intermediate_dirs("bin")
    ['bin']
    >>> get_all_intermediate_dirs("bin/")
    ['bin']
    >>> get_all_intermediate_dirs("bin/abc")
    ['bin/abc', 'bin']
    >>> get_all_intermediate_dirs("bin/abc/")
    ['bin/abc', 'bin']
    >>> get_all_intermediate_dirs("bin/abc/def")
    ['bin/abc/def', 'bin/abc', 'bin']
    >>> get_all_intermediate_dirs("bin/abc/def/")
    ['bin/abc/def', 'bin/abc', 'bin']
    """
    path = path.strip("/")
    intermediate_dirs = [path]

    intermediate_file = os.path.dirname(path)
    while intermediate_file:
        intermediate_file = intermediate_file.rstrip("/")
        intermediate_dirs.append(intermediate_file)

        intermediate_file = os.path.dirname(intermediate_file)

    return intermediate_dirs
