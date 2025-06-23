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
import os
import tempfile
from typing import Dict


class TLSCertificateManager:
    """TLS 证书管理器"""

    def __init__(self, tls_cfg: Dict[str, str]):
        # TLS 配置，包含证书内容 & 相关选项
        # 可能存在的 key：
        # - ca: CA 证书内容
        # - cert: 服务端证书内容
        # - key: 私钥内容
        # - check_hostname: 是否检查主机名，默认为 False
        self.tls_cfg = tls_cfg
        # 证书写入的临时文件路径
        self.tmp_cert_filepaths = {}

    def __enter__(self):
        if ca := self.tls_cfg.get("ca"):
            self.tmp_cert_filepaths["ca"] = self._write_to_tmp_file(ca)

        if cert := self.tls_cfg.get("cert"):
            self.tmp_cert_filepaths["cert"] = self._write_to_tmp_file(cert)

        if key := self.tls_cfg.get("key"):
            self.tmp_cert_filepaths["key"] = self._write_to_tmp_file(key)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for path in self.tmp_cert_filepaths.values():
            try:
                os.remove(path)
            except (FileNotFoundError, PermissionError):
                pass

    def get_django_ssl_options(self) -> Dict[str, str]:
        """Get Django SSL options"""
        # 重新构造以避免修改原始配置
        opts = {k: v for k, v in self.tmp_cert_filepaths.items() if k in ["ca", "cert", "key"]}
        # 允许关闭主机名检查，因为证书可能不是由权威机构颁发的（仅当有任意证书时需要）
        if opts:
            opts["check_hostname"] = self.tls_cfg.get("check_hostname", False)

        return opts

    @staticmethod
    def _write_to_tmp_file(content: str) -> str:
        """将证书内容写入临时文件"""
        f = tempfile.NamedTemporaryFile(mode="wb", delete=False)  # noqa: SIM115
        f.write(base64.b64decode(content))
        f.close()
        # 设置文件权限
        os.chmod(f.name, 0o600)

        return f.name
