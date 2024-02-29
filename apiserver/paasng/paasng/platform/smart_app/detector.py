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
import base64
import hashlib
import logging
import re
import zipfile
from dataclasses import dataclass
from itertools import product
from os import PathLike
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import yaml
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from yaml import YAMLError

from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.constants import AppDescPluginType, AppSpecVersion
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.path import PathProtocol
from paasng.platform.sourcectl.models import SPStat
from paasng.platform.sourcectl.package.client import BinaryTarClient, ZipClient

logger = logging.getLogger(__name__)


@dataclass
class DetectResult:
    """
    :param str relative_path: relative_path of the app description file and the version of meta file
    :param AppSpecVersion version: the version of app description file
    """

    relative_path: str
    version: AppSpecVersion


class AppYamlDetector:
    _regexes = {
        AppSpecVersion.VER_1: r"(^(?<=[/\\\\])?|(?<=[/\\\\]))app\.ya?ml$",
        AppSpecVersion.VER_2: r"(^(?<=[/\\\\])?|(?<=[/\\\\]))app_desc\.ya?ml$",
    }

    @classmethod
    def detect(cls, filepath: str, spec_version: AppSpecVersion = AppSpecVersion.VER_2) -> Optional[DetectResult]:
        """Detect whether the file path meets the specification of `app.yaml`

        if matched, return DetectResult, else, return None
        """
        regex = cls._regexes[spec_version]
        result = re.split(regex, filepath)
        if len(result) > 1:
            return DetectResult(relative_path=result[0], version=spec_version)
        return None


class SourcePackageStatReader:
    """Read local source package's stats"""

    def __init__(self, path: PathLike):
        self.path = Path(path)

    @cached_property
    def accessor(self):
        if zipfile.is_zipfile(self.path):
            return ZipClient
        return BinaryTarClient

    def get_meta_info(self) -> Tuple[str, Dict]:
        """
        Get package's meta info which was stored in file 'app.yaml'

        :returns: Tuple[str, Dict]
        - the relative path of app.yaml (to the root dir in the tar file), "./" is returned by default
        - the raw meta info of source package, `{}` is returned by default
        :raises: ValidationError when meta info is not valid YAML
        """
        relative_path = "./"

        with self.accessor(self.path) as archive:
            try:
                # 根据约定, application description file 应当在应用的外层目录, 排序后可以更快地找到 application description file
                existed_filenames = sorted(archive.list())
            except RuntimeError:
                logger.warning("file: %s is not a valid tar file.", self.path)
                return relative_path, {}

            for spec_version, filename in product([AppSpecVersion.VER_2, AppSpecVersion.VER_1], existed_filenames):
                result = AppYamlDetector.detect(filename, spec_version)
                if result is not None:
                    app_filename = filename
                    relative_path = result.relative_path
                    break
            else:
                # If not description file can be found, return empty info
                return relative_path, {}

            meta_file = archive.read_file(app_filename)
            if not meta_file:
                raise RuntimeError("file: {} can not be extracted".format(app_filename))

            try:
                meta_info = yaml.load(meta_file)
            except YAMLError:
                logger.exception(_("应用描述文件内容不是有效 YAML 格式"))
                raise ValidationError(_("应用描述文件内容不是有效 YAML 格式"))

            logo_b64data = self._load_logo(archive=archive, relative_path=relative_path)
            if logo_b64data:
                meta_info["logo_b64data"] = logo_b64data
                meta_info["logoB64data"] = logo_b64data

            return relative_path, meta_info

    def _try_extract_version(self, meta_info: Dict) -> Optional[str]:
        """Try extracting version from meta info"""
        if not meta_info:
            return None

        try:
            desc = get_desc_handler(meta_info).app_desc
        except DescriptionValidationError as e:
            logger.warning("failed to extract version from app_desc, detail: %s", e)
            return None
        # smart version was stored as one of app's plugin
        plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
        return plugin["data"] if plugin else None

    def compute_sha256_digest(self) -> str:
        """Compute package's sha256 digest"""
        # generate signature
        sha256_hash = hashlib.sha256()
        with open(self.path, mode="rb") as fh:
            for byte_block in iter(lambda: fh.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def read(self) -> SPStat:
        """Return source package's stats object"""
        logger.debug("parsing source package's stats object.")
        relative_path, meta_info = self.get_meta_info()
        # 当从源码包解析 app version 失败时, 需要由其他途径保证能获取到 version. 例如上传源码包的接口中的 version 参数
        version = self._try_extract_version(meta_info) or ""
        return SPStat(
            name=self.path.name,
            version=version,
            size=self.path.stat().st_size,
            meta_info=meta_info,
            relative_path=relative_path,
            sha256_signature=self.compute_sha256_digest(),
        )

    @staticmethod
    def _load_logo(archive: Union[ZipClient, BinaryTarClient], relative_path: str) -> Optional[str]:
        logo_b64data = None
        try:
            # Q: 为什么需要进行 base64 编码?
            # A: 因为 meta_info 会被归档存储进数据库, bytes 类型无法序列化成 json
            logo_b64data = "base64," + base64.b64encode(archive.read_file(relative_path + "logo.png")).decode()
        except (RuntimeError, KeyError):
            logger.exception("Can't read logo.png.")
        return logo_b64data


class ManifestDetector:
    """协助生成 S-Mart 包文件清单的工具类"""

    def __init__(
        self,
        package_root: PathProtocol,
        app_description: ApplicationDesc,
        relative_path: str = "./",
        source_dir: str = "./src",
    ):
        """
        :param package_root: 源码包根路径
        :param ApplicationDesc app_description: 应用描述对象
        :param relative_path: app_description file 相对于 源码包根路径 的路径(只对 S-Mart应用 有意义, 普通应用是 ./)
        :param source_dir: 模块源代码相对于 app_description file 的路径
        """
        self.package_root = package_root
        self.app_description = app_description
        self.relative_path = relative_path
        self.source_dir = source_dir

    def detect(self):
        """探测源码的目录结构, 清单记录的所有路径均是对 源码根目录 的相对路径"""
        manifest = dict(
            app_desc=self.detect_app_desc(),
            procfile=self.detect_procfile(),
            source_dir=self.make_relative_key(self.package_root / self.relative_path / self.source_dir),
            cert=self.detect_certs() or None,
            encryption=self.detect_encryption() or None,
        )
        dependency = self.detect_dependency()
        if dependency:
            manifest["dependency"] = dependency
        return manifest

    def detect_procfile(self) -> str:
        """探测源码包中的 Procfile 的路径"""
        # 优先探测用户在源码中定义的 Procfile, 如果文件被加密, 则使用由 PaaS 注入的 Procfile
        possible_keys = [
            self.package_root / self.relative_path / self.source_dir / "Procfile",
            self.package_root / self.relative_path / "Procfile",
        ]
        for key in possible_keys:
            if key.exists():
                return self.make_relative_key(key)
        raise KeyError("Procfile not found.")

    def detect_app_desc(self) -> str:
        """探测源码包中的 app.yaml 的路径"""
        possible_keys = [
            self.package_root / self.relative_path / "app_desc.yaml",
            self.package_root / self.relative_path / "app_desc.yml",
            self.package_root / self.relative_path / "app.yaml",
            self.package_root / self.relative_path / "app.yml",
        ]
        for key in possible_keys:
            if key.exists():
                return self.make_relative_key(key)
        raise KeyError("app_desc not found.")

    def detect_dependency(self) -> Optional[str]:
        """探测源码包中的 requirements.txt(python)、package.json(node)、go.mod(golang)"""
        possible_keys = [
            self.package_root / self.relative_path / self.source_dir / "requirements.txt",
            self.package_root / self.relative_path / "requirements.txt",
        ]
        for key in possible_keys:
            if key.exists():
                return self.make_relative_key(key)
        return None

    def detect_certs(self) -> Dict[str, str]:
        """探测源码包中的证书文件"""
        prefix = self.package_root / self.relative_path / "cert"
        if not prefix.exists() or not prefix.is_dir():
            return {}
        detector: Dict[str, PathProtocol] = {
            "root": prefix / "bk_root_ca.cert",
            "intermediate": prefix / "bk_saas_sign.cert",
            "saas": prefix / "saas.cert",
            "key": prefix / "saas.key",
        }
        results: Dict[str, str] = {}
        for k, v in detector.items():
            if v.exists() and v.is_file():
                results[k] = self.make_relative_key(v)
        return results

    def detect_encryption(self) -> Dict[str, str]:
        """探测源码包中的加密配置"""
        prefix = self.package_root / self.relative_path / "conf"
        if not prefix.exists() or not prefix.is_dir():
            return {}
        detector: Dict[str, PathProtocol] = {
            "sha256": prefix / "SHA256",
            "package": prefix / "package.conf",
            "saas_priv": prefix / "saas_priv.txt",
            "signature": prefix / "signature",
        }
        results: Dict[str, str] = {}
        for k, v in detector.items():
            if v.exists() and v.is_file():
                results[k] = self.make_relative_key(v)
        return results

    def make_relative_key(self, key: PathProtocol) -> str:
        # 增加 "./" 以明确表示 key 是相对源码根目录的相对路径.
        return "./" + str(key.relative_to(self.package_root / self.relative_path))
