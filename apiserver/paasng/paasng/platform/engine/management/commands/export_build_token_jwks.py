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

"""导出构建 token 签名密钥的公钥集合（JWKS），供部署时分发给各集群的镜像代理

JWKS 包含 BUILD_TOKEN_SIGNING_KEYS 中的全部公钥，轮换期间新旧 token 均可被校验。
"""

import json

from django.core.management.base import BaseCommand, CommandError

from paasng.platform.engine.configurations.build_token import load_signing_key_set


class Command(BaseCommand):
    help = "导出构建 token 签名密钥的公钥集合（JWKS）"

    def add_arguments(self, parser):
        parser.add_argument("--output", help="JWKS 的保存路径，默认输出到标准输出")

    def handle(self, output, *args, **options):
        keyset = load_signing_key_set()
        if not keyset:
            raise CommandError("BUILD_TOKEN_SIGNING_KEYS is not configured")

        content = json.dumps(keyset.to_jwks(), indent=2)
        if output:
            with open(output, "w") as f:
                f.write(content + "\n")
        else:
            self.stdout.write(content)

        kids = ", ".join(k.kid for k in keyset.keys)
        self.stderr.write(f"Exported {len(keyset.keys)} key(s): {kids}; active kid: {keyset.active.kid}")
