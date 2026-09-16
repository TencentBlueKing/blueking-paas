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

"""``app-spark-forgejo`` entry: ready / init / verify."""

from __future__ import annotations

import argparse

from app_spark_forgejo.common import wait_ready
from app_spark_forgejo.init import initialise
from app_spark_forgejo.verify import verify


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="app-spark-forgejo",
        description="Initialise and verify the App-Spark Forgejo Git host.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ready", help="Block until /api/healthz answers 200")
    sub.add_parser("init", help="Create admin, service account and org (idempotent)")
    sub.add_parser("verify", help="Check server-side invariants against a running instance")

    args = parser.parse_args(argv)
    if args.command == "ready":
        wait_ready()
        print("Forgejo is ready.")
        return
    if args.command == "init":
        initialise()
        return
    verify()
