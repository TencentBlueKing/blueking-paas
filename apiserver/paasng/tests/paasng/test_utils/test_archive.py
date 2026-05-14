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

import zipfile
from pathlib import Path

import pytest

from paasng.utils.archive import UnsafeArchiveError, safe_extract_zip


class TestSafeExtractZip:
    @pytest.fixture
    def dest_dir(self, tmp_path: Path) -> Path:
        """解压目标目录"""
        return tmp_path / "dest"

    @staticmethod
    def _make_zip(zip_path: Path, members: dict) -> Path:
        """根据 {成员名: 内容} 创建一个 zip 文件, 内容为 None 时表示目录"""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in members.items():
                if content is None:
                    # 目录成员, 以 "/" 结尾
                    zi = zipfile.ZipInfo(name if name.endswith("/") else name + "/")
                    zf.writestr(zi, b"")
                else:
                    zf.writestr(name, content)
        return zip_path

    def test_extract_valid_zip(self, tmp_path: Path, dest_dir: Path):
        """测试正常的 zip 文件能够正确解压"""
        members = {
            "file1.txt": b"Hello, World!",
            "./file2.txt": b"File with dot",
            "dir/": None,
            "dir/file3.txt": b"Another file",
            "dir/./file4.txt": b"File with dot in dir",
        }
        zip_path = self._make_zip(tmp_path / "test.zip", members)
        safe_extract_zip(zip_path, dest_dir)

        # 验证解压后的文件内容
        assert (dest_dir / "file1.txt").read_bytes() == b"Hello, World!"
        assert (dest_dir / "file2.txt").read_bytes() == b"File with dot"
        assert (dest_dir / "dir").is_dir()
        assert (dest_dir / "dir/file3.txt").read_bytes() == b"Another file"
        assert (dest_dir / "dir/file4.txt").read_bytes() == b"File with dot in dir"

    def test_reject_absolute_path_member(self, tmp_path: Path, dest_dir: Path):
        """测试包含绝对路径成员的 zip 文件会被拒绝"""
        members = {
            "/absolute.txt": b"Should not be extracted",
        }
        zip_path = self._make_zip(tmp_path / "test.zip", members)
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zip_path, dest_dir)

    def test_reject_parent_traversal_member(self, tmp_path: Path, dest_dir: Path):
        """测试包含路径穿越成员的 zip 文件会被拒绝"""
        members = {
            "../evil1.txt": b"Should not be extracted",
        }
        zip_path = self._make_zip(tmp_path / "test.zip", members)
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zip_path, dest_dir)

    def test_reject_complex_traversal_member(self, tmp_path: Path, dest_dir: Path):
        """测试包含复杂路径穿越成员的 zip 文件会被拒绝"""
        members = {
            "dir/../../evil2.txt": b"Should not be extracted",
        }
        zip_path = self._make_zip(tmp_path / "test.zip", members)
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zip_path, dest_dir)

    def test_no_partial_extraction_on_unsafe_member(self, tmp_path: Path, dest_dir: Path):
        """测试当 zip 文件中包含不安全成员时，不会解压任何成员"""
        members = {
            "good.txt": b"Good file",
            "../evil.txt": b"Should not be extracted",
        }
        zip_path = self._make_zip(tmp_path / "test.zip", members)
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zip_path, dest_dir)

        # dest_dir 应该保持为空, 没有任何成员被解压
        assert dest_dir.is_dir()
        assert not any(dest_dir.iterdir())
        # 父目录中也不应该有 evil.txt
        assert not (dest_dir.parent / "evil.txt").exists()
