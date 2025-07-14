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

import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePath, PureWindowsPath
from typing import Callable, ContextManager, Iterator, List, Optional, Tuple, Union

from paasng.utils.patternmatcher import Pattern

logger = logging.getLogger(__name__)
ExcludeChecker = Callable[[str], bool]


class DockerIgnore:
    """DockerIgnore provide a test for whether to ignore a file.

    :param content: content of .dockerignore
    :param whitelist: if something match .dockerignore but also in whitelist, will not be ignored.
    """

    def __init__(self, content: str, whitelist: Optional[List[str]] = None):
        self.raw_content = content
        self.content = self._parse_content(content)
        self.patterns: List[Tuple[bool, Pattern]] = []
        self.whitelist = [PurePath(path) for path in (whitelist or [])]
        for pattern_str in self.content:
            pattern_str_new = pattern_str
            invert = pattern_str.startswith("!")
            if invert:
                pattern_str_new = pattern_str[1:]
            self.patterns.append((invert, Pattern(pattern_str_new)))

    def should_ignore(self, filename: str) -> bool:
        """detect whether to ignore given filename,
        return True to ignore, False to include
        """
        if PurePath(filename) in self.whitelist:
            return False

        should_ignore = False
        for invert, pattern in self.patterns:
            matched = pattern.match(filename)
            if matched:
                should_ignore = not invert
        return should_ignore

    @classmethod
    def clean_path(cls, path: str) -> str:
        """clean_path returns the shortest path name equivalent to path by purely lexical processing.
        See also: golang filepath.Clean()
        """
        # PureWindowsPath 实现了:
        # 1. 同时兼容 \\ 和 / 路径分隔符
        # 2. 解析 windows 光驱位
        # 3. 将多个路径分隔符替换成一个分隔符, (例如 a//b\\\\c -> a/b/c)
        sep = "/"
        p = PureWindowsPath(path)
        # PureWindowsPath 虽然兼容 \\ 和 // 路径分隔符, 但是会将 posix-like 的绝对路径转换成 "\\"
        if p.drive != "" or (len(p.parts) > 1 and p.parts[0] == "\\"):
            # 移除 windows 光驱位或 posix-like 的绝对路径
            path = sep.join(p.parts[1:])
        else:
            path = sep.join(p.parts)
        # 解析 .. 和 . 等相对路径
        path = os.path.normpath(path)
        return path

    @classmethod
    def _parse_content(cls, content: str) -> List[str]:
        patterns = []
        for line in content.splitlines():
            # Lines starting with # (comments) are ignored before processing
            if line.startswith("#"):
                continue
            # Empty line
            pattern = line.strip()
            if pattern.strip() == "":
                continue
            invert = pattern.startswith("!")
            if invert:
                pattern = pattern[1:].strip()
            if len(pattern) > 0:
                pattern = cls.clean_path(pattern)
            if invert:
                pattern = "!" + pattern
            patterns.append(pattern)
        return patterns


def compress_directory_ext(
    source_path: Union[str, Path], target_path: Union[str, Path], should_ignore: Optional[ExcludeChecker] = None
):
    """Compress a directory using tar+gz

    :param source_path: dir to be compressed
    :param target_path: tarball output path
    :param should_ignore: an optional checker the check whether compress a file in source_path

    If the should_ignore parameter is not provided, the tar command will be used for packaging, as it is faster.
    """
    source_path = Path(source_path)
    target_path = Path(target_path)

    # tar command wil faster than tarball library
    if should_ignore is None:
        return compress_directory(source_path, target_path)

    def compress_core(tarball: tarfile.TarFile, p: Path):
        arcname = str(p.relative_to(source_path))
        if should_ignore and should_ignore(arcname):
            return
        if p.is_dir():
            for sub in p.iterdir():
                compress_core(tarball, sub)
        else:
            tarball.add(p, arcname)

    try:
        from gzip import GzipFile
    except ImportError:
        raise tarfile.CompressionError("gzip module is not available")

    with GzipFile(target_path, mode="w", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w|") as tf:  # type: ignore
        compress_core(tf, source_path)
        return None


def compress_directory(source_path, target_path):
    """Compress a directory using tar command"""
    # Use tar command to compress
    # Add "GZIP=-n" to disable gzip timestamp
    # see: https://serverfault.com/questions/110208/different-md5sums-for-same-tar-contents
    p = subprocess.Popen(
        ["tar", "--exclude=.svn", "-czf", str(target_path), "-C", str(source_path), "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"GZIP": "-n"},
        encoding="utf-8",
    )
    _, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("Unable to package source, error: %s" % stderr)


def uncompress_directory(source_path, target_path):
    """uncompress a tar file using tar command"""
    source_path = os.path.abspath(source_path)
    target_path = os.path.abspath(target_path)
    # -m, --touch                don't extract file modified time
    p = subprocess.Popen(
        ["tar", "-m", "-xf", str(source_path), "-C", str(target_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    _, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("Unable to unpackage source, error: %s" % stderr)


def _generate_temp_dir_(suffix=None) -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mkdtemp(suffix=suffix))
        logger.debug("Generating temp path: %s", path)
        yield path
    finally:
        if path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[Path]] = contextmanager(_generate_temp_dir_)


def _generate_temp_file_(suffix="") -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mktemp(suffix=suffix))
        logger.debug("Generating temp path: %s", path)
        yield path
    finally:
        if path and path.exists():
            path.unlink()


generate_temp_file: Callable[..., ContextManager[Path]] = contextmanager(_generate_temp_file_)


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
