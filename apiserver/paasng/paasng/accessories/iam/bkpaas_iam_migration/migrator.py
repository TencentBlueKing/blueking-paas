# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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

import codecs
import json
import os
import sys

from django.conf import settings
from iam.contrib.iam_migration import exceptions
from iam.contrib.iam_migration.migrator import renders
from iam.contrib.iam_migration.utils import do_migrate


class BKPaaSIAMMigrator:
    """
    bkpaas 定制化 IAM Migrator

    由于 bkpaas 配置项与 IAM 中需要的项含义不同，且无指定的方法，因此特殊定制
    主要差异项：APP_CODE -> IAM_APP_CODE, SECRET_KEY -> IAM_APP_SECRET
    """

    def __init__(self, migration_json):
        self.migration_json = migration_json

    def migrate(self):
        app_code = settings.IAM_APP_CODE
        app_secret = settings.IAM_APP_SECRET

        USE_APIGATEWAY = getattr(settings, "BK_IAM_USE_APIGATEWAY", False)
        if USE_APIGATEWAY:
            do_migrate.enable_use_apigateway()
            iam_host = getattr(settings, "BK_IAM_APIGATEWAY_URL", "")
            if iam_host == "":
                raise exceptions.MigrationFailError("settings.BK_IAM_APIGATEWAY_URL should be setted")
        else:
            iam_host = settings.BK_IAM_V3_INNER_URL

        # only trigger migrator at db migrate
        if "migrate" not in sys.argv:
            return

        if getattr(settings, "BK_IAM_SKIP", False):
            return

        json_path = getattr(settings, "BK_IAM_MIGRATION_JSON_PATH", "support-files/iam/")
        file_path = os.path.join(settings.BASE_DIR, json_path, self.migration_json)

        with codecs.open(file_path, mode="r", encoding="utf-8") as fp:
            data = json.load(fp=fp)

        # data pre render
        for op in data["operations"]:
            if op["operation"] in renders:
                renders[op["operation"]](op["data"])

        ok, _ = do_migrate.api_ping(iam_host)
        if not ok:
            raise exceptions.NetworkUnreachableError("bk iam ping error")

        ok = do_migrate.do_migrate(data, iam_host, app_code, app_secret)
        if not ok:
            raise exceptions.MigrationFailError("iam migrate fail")
