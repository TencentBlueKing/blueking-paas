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

import abc
import logging
import os
import os.path
import re
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import IO, List, Literal, Optional, Union

from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.package.downloader import download_file_via_url
from paasng.platform.sourcectl.utils import generate_temp_dir, uncompress_directory
from paasng.utils.text import remove_prefix

logger = logging.getLogger(__name__)


class BasePackageClientError(Exception):
    """The base error class for package clients."""


class InvalidPackageFileFormatError(Exception):
    """The package file is not in a valid format, it might be corrupt."""


class FileDoesNotExistError(KeyError, RuntimeError):
    """The file does not exist.

    This exception is used to maintain compatibility with existing code that handles missing files.
    TODO: Consider unifying exception handling for read_file.
    """


class BasePackageClient(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """从版本库里读取指定位置的文件"""
        raise NotImplementedError

    @abc.abstractmethod
    def export(self, local_path: str):
        """在 local_path 下创建当前版本库的副本"""
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        """关闭与源码包的链接"""

    @abc.abstractmethod
    def list(self) -> List[str]:
        """查询源码包中含有的所有文件"""

    def __enter__(self):
        """提供遵循 closing 协议的上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class TarClient(BasePackageClient):
    """基于本地 tar 包初始化的 client"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        file_obj: Optional[IO] = None,
        mode: str = "r:*",
        relative_path: str = "./",
    ):
        """从本地文件或 IO Stream 对象创建操作该 Tar 包的客户端
        :param file_path: 本地的 tar 包存储路径
        :param file_obj: Tar 包的 IO Stream 对象
        :param mode: tar 包操作的模式, 具体请看 TarFile.open 的注解
        :param relative_path: tar 包内容的相对位置, 如果压缩时将目录也打包进来, 入目录名是 foo, 那么 relative_path = 'foo/'
        """
        if not file_path and not file_obj:
            raise ValueError("nothing to open")
        if file_path and file_obj:
            raise ValueError("file_path and file_obj cannot be provided at the same time")
        self.tar = tarfile.open(name=file_path, fileobj=file_obj, mode=mode)  # noqa: SIM115
        self.relative_path = relative_path

    def read_file(self, file_path: str) -> bytes:
        """读取 Tar 包指定位置的文件"""
        # 去除多余的相对路径, 计算最简化的相对路径
        key = os.path.relpath(file_path)
        key = os.path.join(self.relative_path, key)
        file = self.tar.extractfile(key)
        if not file:
            raise FileDoesNotExistError(f"filename: {file_path} Don't exists.")
        return file.read()

    def export(self, local_path: str):
        """导出指定当前 Tar 包到local_path"""
        # set filter="data" explicitly to fix CVE-2007-4559
        # see https://docs.python.org/3.11/library/tarfile.html#tarfile-extraction-filter
        self.tar.extractall(local_path, filter="data")  # type: ignore[call-arg]

    def close(self):
        """关闭文件句柄"""
        self.tar.close()

    def list(self) -> List[str]:
        return self.tar.getnames()


class BinaryTarClient(BasePackageClient):
    """A tarball extractor faster than the tarfile library (which written by pure python code).

    When handling big tarball(>=100mb), will faster than tarfile 10 seconds in the special testcase.
    """

    def __init__(self, file_path: Union[str, Path]):
        self.filepath = Path(file_path)

    def read_file(self, filename) -> bytes:
        """Extract a filename from the archive as bytes.

        :param filename: the filename need to be extracted.
        :return: bytes contents of the file.
        :raises InvalidPackageFileFormatError: The file is not a valid tar file, it's content
            might be corrupt.
        :raise RuntimeError: Raised if unexpected errors occur.
        """
        with generate_temp_dir() as temp_dir:
            p = subprocess.Popen(
                f'tar -xf "{self.filepath.absolute()}" -C "{temp_dir.absolute()}" "{filename}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            _, stderr = p.communicate()
            if p.returncode != 0:
                if self._is_invalid_file_format_error(stderr):
                    raise InvalidPackageFileFormatError()
                if self._is_not_found_error(stderr):
                    raise FileDoesNotExistError(f"Failed to extractfile from the tarball, error: {stderr!r}")
                else:
                    raise RuntimeError(f"Failed to extractfile from the tarball, error: {stderr!r}")

            filepath = temp_dir / filename

            # Check if the file is a symbolic link and it's inside the directory
            real_path = os.path.realpath(filepath)
            if os.path.commonpath([temp_dir, real_path]) != str(temp_dir):
                raise RuntimeError(f"Extracted file {filepath} is outside the target directory.")
            return filepath.read_bytes()

    def export(self, local_path: str):
        """Extract all members from the archive to the current working directory

        :param working_dir: working directory
        :raise RuntimeError: Raised if unexpected errors occur.
        """
        uncompress_directory(source_path=self.filepath, target_path=local_path)

        # Security check: traverse the directory to check if any link files is outside the target directory
        for dirpath, dirnames, filenames in os.walk(local_path):
            for name in dirnames + filenames:
                if not Path(os.path.join(dirpath, name)).is_symlink():
                    continue
                real_path = os.path.realpath(os.path.join(dirpath, name))
                if os.path.commonpath([local_path, real_path]) != str(local_path):
                    raise RuntimeError(f"Extracted file {real_path} is outside the target directory.")

    def close(self):
        """Nothing need to close."""

    def list(self, tarfile_like: bool = True) -> List[str]:
        """List the file of the tarball

        :param tarfile_like: tar 命令与 tarfile 的差异点在于, tar 命令返回目录时会在末尾带上 "/",
            如果设置 tarfile_like = True, 则自动去除末尾的 "/"
        :raises InvalidPackageFileFormatError: The file is not a valid tar file, it's content
            might be corrupt.
        """
        p = subprocess.Popen(
            f'tar -tf "{self.filepath.absolute()}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            if self._is_invalid_file_format_error(stderr):
                raise InvalidPackageFileFormatError()
            raise RuntimeError(f"Failed to read from the tarball, error: {stderr!r}")
        items = stdout.strip().split("\n")
        return items if not tarfile_like else [item.rstrip(os.path.sep) for item in items]

    @staticmethod
    def _is_invalid_file_format_error(message: str) -> bool:
        """Check if the stderr message indicates an invalid file format."""
        return bool(re.search(r"tar:.* not look like a tar archive", message))

    @staticmethod
    def _is_not_found_error(message: str) -> bool:
        """Check if the stderr message indicates a file not found."""
        return bool(re.search(r"tar:.*: Not found in archive", message))


class ZipClient(BasePackageClient):
    """基于本地 zip 包初始化的 client"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        file_obj: Optional[IO[bytes]] = None,
        mode: Literal["r", "w", "x", "a"] = "r",
        relative_path: str = "./",
    ):
        """从本地文件或 IO Stream 对象创建操作该 Zip 包的客户端
        :param file_path: 本地的 Zip 包存储路径
        :param file_obj: Zip 包的 IO Stream 对象
        :param mode: zip 包操作的模式, 具体请看 zipfile.Zipfile 的注解
        :param relative_path: tar 包内容的相对位置, 如果压缩时将目录也打包进来, 入目录名是 foo, 那么 relative_path = 'foo/'
        """
        if not file_path and not file_obj:
            raise ValueError("nothing to open")
        if file_path and file_obj:
            raise ValueError("file_path and file_obj cannot be provided at the same time")
        file_ = file_path or file_obj
        assert file_
        self.zip_ = zipfile.ZipFile(file=file_, mode=mode)
        # 由于 zipfile 不会记录 "./" 这样的前缀, 因此需要重新去除 relative_path 中的相对路径前缀
        self.relative_path = remove_prefix(relative_path, "./")

    def read_file(self, file_path: str) -> bytes:
        """读取 zip 包指定位置的文件"""
        # 去除多余的相对路径, 计算最简化的相对路径
        key = os.path.relpath(file_path)
        key = os.path.join(self.relative_path, key)
        try:
            info = self.zip_.getinfo(key)
        except KeyError as e:
            raise FileDoesNotExistError(f"filename: {file_path} Don't exists.") from e

        return self.zip_.read(info)

    def export(self, local_path: str):
        self.zip_.extractall(local_path)

    def close(self):
        self.zip_.close()

    def list(self) -> List[str]:
        return self.zip_.namelist()


class GenericLocalClient(BasePackageClient):
    """同时支持 zip, tar 格式的 SourcePackage 客户端"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        file_obj: Optional[IO[bytes]] = None,
        mode: str = "r",
        relative_path: str = "./",
    ):
        """从本地文件或 IO Stream 对象创建操作该 Zip 包的客户端
        :param file_path: 本地的 tar 包存储路径
        :param file_obj: Zip 包的 IO Stream 对象
        :param mode: zip 包操作的模式, 具体请看 zipfile.Zipfile 的注解
        :param relative_path: tar 包内容的相对位置, 如果压缩时将目录也打包进来, 入目录名是 foo, 那么 relative_path = 'foo/'
        """
        if not file_path and not file_obj:
            raise ValueError("nothing to open")
        if file_path and file_obj:
            raise ValueError("file_path and file_obj cannot be provided at the same time")

        self._client = self.detect_client(file_path, file_obj)(file_path, file_obj, mode, relative_path)

    @staticmethod
    def detect_client(file_path: Optional[str] = None, file_obj: Optional[IO] = None):
        if file_path:
            is_zipfile = zipfile.is_zipfile(file_path)
        elif file_obj:
            location = file_obj.tell()
            is_zipfile = zipfile.is_zipfile(file_obj)
            file_obj.seek(location)
        else:
            raise ValueError("nothing to open")
        if is_zipfile:
            return ZipClient
        else:
            return TarClient

    def read_file(self, file_path: str) -> bytes:
        return self._client.read_file(file_path)

    def export(self, local_path: str):
        return self._client.export(local_path)

    def close(self):
        return self._client.close()

    def list(self) -> List[str]:
        return self._client.list()


class GenericRemoteClient(GenericLocalClient):
    """操作远程 tar 包的 通用 client"""

    def __init__(self, url: str, relative_path: str = "./"):
        self.filepath = Path(tempfile.mktemp())
        download_file_via_url(url, local_path=self.filepath)

        try:
            super().__init__(file_path=str(self.filepath), mode="r", relative_path=relative_path)
        except Exception:
            logger.exception(f"Can't handle a tar/zip file from remote path: {url}")
            if self.filepath.exists():
                self.filepath.unlink()

    def close(self):
        """关闭文件句柄并清理本地文件"""
        super().close()
        if self.filepath.exists():
            self.filepath.unlink()


# TODO: 只保留 GenericRemoteClient
storage_engine_maps = {
    "GenericRemoteClient": GenericRemoteClient,
    # LocalClient are only For Test
    "GenericLocalClient": GenericLocalClient,
    "TarClient": TarClient,
    "ZipClient": ZipClient,
    # TODO: 确认生产环境数据库中是否有这个值, 如果有, 则进行替换后去除该选项
    "S3TarClient": GenericRemoteClient,
    "HTTPTarClient": GenericRemoteClient,
}


def get_client(package: SourcePackage) -> BasePackageClient:
    """根据源码包存储信息, 获取对应的源码包操作客户端"""
    client_class = storage_engine_maps[package.storage_engine]
    return client_class(package.storage_path, relative_path=package.relative_path)
