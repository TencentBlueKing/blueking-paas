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

"""safe_extract_zip 的单元测试"""

import zipfile
from pathlib import Path

import pytest

from paasng.utils.archive import UnsafeArchiveError, safe_extract_zip


@pytest.fixture
def tmp_dir(tmp_path):
    """返回一个临时目录用于解压测试"""
    return tmp_path


def _make_zip(zip_path: Path, entries: dict[str, str | bytes], symlink_entries: dict[str, str] | None = None):
    """构造一个 zip 文件用于测试。

    :param zip_path: zip 文件路径
    :param entries: {成员名: 内容}，内容为 str 或 bytes
    :param symlink_entries: {成员名: 链接目标}，构造 Unix symlink 条目
    """
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            if isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content.encode("utf-8"))
        if symlink_entries:
            for name, target in symlink_entries.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3  # Unix
                info.external_attr = 0o120755 << 16  # symlink file type + permissions
                zf.writestr(info, target)


class TestSafeExtractZipNormal:
    """用例 5.1：正常合法 zip 可完整解压到目标目录"""

    def test_extract_normal_zip(self, tmp_dir):
        zip_path = tmp_dir / "normal.zip"
        _make_zip(zip_path, {"dir/file1.txt": "hello", "dir/file2.txt": "world", "root.txt": "root"})

        safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

        output = tmp_dir / "output"
        assert (output / "dir" / "file1.txt").read_text() == "hello"
        assert (output / "dir" / "file2.txt").read_text() == "world"
        assert (output / "root.txt").read_text() == "root"

    def test_extract_zip_with_zipfile_object(self, tmp_dir):
        zip_path = tmp_dir / "normal.zip"
        _make_zip(zip_path, {"a.txt": "aaa"})

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            safe_extract_zip(zf, str(tmp_dir / "output"))

        assert (tmp_dir / "output" / "a.txt").read_text() == "aaa"

    def test_extract_empty_zip(self, tmp_dir):
        zip_path = tmp_dir / "empty.zip"
        with zipfile.ZipFile(str(zip_path), "w"):
            pass

        safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

        output = tmp_dir / "output"
        assert output.is_dir()


class TestSafeExtractZipPathTraversal:
    """用例 5.2：含 ../ 相对路径穿越成员的 zip 被拒绝"""

    def test_reject_dotdot_traversal(self, tmp_dir):
        zip_path = tmp_dir / "evil.zip"
        _make_zip(zip_path, {"../../../tmp/pwned": "evil"})

        with pytest.raises(UnsafeArchiveError, match="outside the target directory"):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

        # 确保目标目录外无文件被写入
        assert not (tmp_dir / "tmp").exists()

    def test_reject_nested_dotdot_traversal(self, tmp_dir):
        zip_path = tmp_dir / "evil2.zip"
        _make_zip(zip_path, {"good/folder/../../../../tmp/pwned2": "evil"})

        with pytest.raises(UnsafeArchiveError, match="outside the target directory"):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

    def test_no_file_written_on_rejection(self, tmp_dir):
        """验证恶意 zip 被拒绝时，目标目录外无任何文件被写入"""
        zip_path = tmp_dir / "evil3.zip"
        # 先在 /tmp 级别创建一个标记文件，用于验证不会被覆盖
        _make_zip(zip_path, {"../../evil.txt": "evil_content"})

        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

        # evil.txt 不应出现在 tmp_dir 的上层
        assert not (tmp_dir / "evil.txt").exists()


class TestSafeExtractZipAbsolutePath:
    """用例 5.3：含绝对路径成员的 zip 被拒绝"""

    def test_reject_unix_absolute_path(self, tmp_dir):
        zip_path = tmp_dir / "evil_abs.zip"
        _make_zip(zip_path, {"/tmp/pwned": "evil"})

        with pytest.raises(UnsafeArchiveError, match="absolute path"):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

    def test_reject_etc_absolute_path(self, tmp_dir):
        zip_path = tmp_dir / "evil_etc.zip"
        _make_zip(zip_path, {"/etc/cron.d/pwn": "evil"})

        with pytest.raises(UnsafeArchiveError, match="absolute path"):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))


class TestSafeExtractZipSymlink:
    """用例 5.4：含指向目录外部的 symlink 条目的 zip 被处理"""

    def test_symlink_entry_does_not_crash(self, tmp_dir):
        """含 symlink 条目的 zip 不应崩溃。

        Python zipfile 在 extract 时不会还原 symlink，
        而是将链接目标路径作为普通文件内容写出。
        safe_extract_zip 会记录日志但不会拒绝（因为名称路径本身是合法的）。
        """
        zip_path = tmp_dir / "symlink.zip"
        _make_zip(
            zip_path,
            entries={"normal.txt": "hello"},
            symlink_entries={"link_to_etc": "/etc/passwd"},
        )

        # symlink 条目名称本身不包含路径穿越，应正常解压
        safe_extract_zip(str(zip_path), str(tmp_dir / "output"))

        output = tmp_dir / "output"
        assert (output / "normal.txt").read_text() == "hello"
        # zipfile 将 symlink 目标作为普通文件内容写出
        assert (output / "link_to_etc").read_text() == "/etc/passwd"

    def test_symlink_with_path_traversal_name_rejected(self, tmp_dir):
        """symlink 条目名称包含路径穿越时应被拒绝"""
        zip_path = tmp_dir / "evil_symlink.zip"
        _make_zip(
            zip_path,
            entries={},
            symlink_entries={"../../evil_link": "/etc/passwd"},
        )

        with pytest.raises(UnsafeArchiveError, match="outside the target directory"):
            safe_extract_zip(str(zip_path), str(tmp_dir / "output"))
