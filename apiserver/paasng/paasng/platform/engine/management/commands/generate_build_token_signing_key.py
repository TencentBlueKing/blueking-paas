# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""生成构建 token 的 Ed25519 签名密钥

私钥只写入 --output 指定的新文件（权限 0600），不输出到终端。

初次配置：把文件内容作为 BUILD_TOKEN_SIGNING_KEYS 的唯一一项。

轮换：
1. 把新私钥追加到 BUILD_TOKEN_SIGNING_KEYS，BUILD_TOKEN_ACTIVE_KID 仍设为旧 kid；
2. 用 export_build_token_jwks 导出同时包含新旧公钥的 JWKS，分发给所有镜像代理；
3. 所有代理加载新 JWKS 后，把 BUILD_TOKEN_ACTIVE_KID 改为新 kid；
4. 旧 kid 签发的 token 全部过期（BUILD_PROCESS_TIMEOUT + 300 秒）后，删除旧私钥并重新导出、分发 JWKS。
"""

import os

from django.core.management.base import BaseCommand, CommandError

from paasng.platform.engine.configurations.build_token import SigningKey


class Command(BaseCommand):
    help = "生成构建 token 的 Ed25519 签名密钥，私钥写入新文件，输出其 kid"

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="私钥（PEM）的保存路径，文件必须不存在")

    def handle(self, output, *args, **options):
        key = SigningKey.generate()
        try:
            fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise CommandError(f"{output} already exists, refuse to overwrite it") from None
        with os.fdopen(fd, "wb") as f:
            f.write(key.to_pem())

        self.stdout.write(f"Private key saved to {output}, kid: {key.kid}")
        self.stdout.write(
            "Append the file content to BUILD_TOKEN_SIGNING_KEYS. When rotating, keep BUILD_TOKEN_ACTIVE_KID "
            "unchanged until all registry proxies have loaded the JWKS containing this key."
        )
