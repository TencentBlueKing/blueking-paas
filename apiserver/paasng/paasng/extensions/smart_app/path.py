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
import zipfile
from os import PathLike
from pathlib import Path, PurePath
from typing import Union

from typing_extensions import Protocol


class PathProtocol(Protocol):
    """PathProtocol 是 pathlib.Path 的子集, 声明了 detector 和 patcher 在操作文件时依赖的协议"""

    def __truediv__(self, other: str) -> 'PathProtocol':
        ...

    def write_text(self, text: str):
        ...

    def exists(self) -> bool:
        ...

    def is_file(self) -> bool:
        ...

    def is_dir(self) -> bool:
        ...

    def relative_to(self, other: 'PathProtocol') -> PurePath:
        ...


class LocalFSPath(PathLike):
    """A PathLike obj, which will auto mkdir parent dir when calling write_text."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def __truediv__(self, other: str):
        return LocalFSPath(self.path / other)

    def write_text(self, text: str):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path.write_text(text)

    def exists(self) -> bool:
        return self.path.exists()

    def is_file(self) -> bool:
        return self.path.is_file()

    def is_dir(self) -> bool:
        return self.path.is_dir()

    def relative_to(self, other) -> PurePath:
        assert isinstance(other, LocalFSPath)
        return self.path.relative_to(other.path)

    def __fspath__(self):
        return self.path.__fspath__()


class ZipPath(PathLike):
    """A PathLike obj describing the relative path in the source zipfile."""

    def __init__(self, source: zipfile.ZipFile, path: Union[str, PurePath]):
        self.source = source
        self.path = PurePath(path).relative_to(".")

    def __truediv__(self, other: str):
        return ZipPath(self.source, self.path / other)

    def write_text(self, text):
        self.source.writestr(str(self.path), text)

    def exists(self) -> bool:
        # zip 没有是否存在的概念, 只需要尝试获取对应的 FileHeader 即可.
        return self.is_file() or self.is_dir()

    def is_file(self) -> bool:
        """Whether this path is a regular file"""
        try:
            self.source.getinfo(str(self.path))
            return True
        except KeyError:
            return False

    def is_dir(self) -> bool:
        """Check whether this path is a directory.

        Zip will store a directory named "a"  as "a/" or "a\\" (for windows)
        But, python zipfile will transfer "\\" to "/", when running in windows system.

        Beside, pathlib will ignore the "/" or "\\" end of path

        So, We need and only need to add "/" to the end of self.path when checking whether this path is a directory.
        """
        try:
            self.source.getinfo(str(self.path) + "/")
            return True
        except KeyError:
            return False

    def relative_to(self, other) -> PurePath:
        assert isinstance(other, ZipPath)
        return self.path.relative_to(other.path)

    def __fspath__(self):
        # For ZipPath, fspath is meaning the relative path in the zipfile, not in the file-system.
        return self.path.__fspath__()
