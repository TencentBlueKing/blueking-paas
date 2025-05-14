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

import datetime

from sqlalchemy.sql import func

from paasng.core.core.storages.sqlalchemy import console_db

from .base import LAppDevelopTimeRecored, LApplication
from .errors import LegacyClientError


def incr_app_dev_time(app_code, hours, creator):
    """Increase an app's dev time spent which is shown in blueking market

    :param app_code: the code of Application object
    :param hours: the hours to be added
    :param creator: creator username
    :type hours: float
    """
    with console_db.session_scope() as session:
        app = session.query(LApplication).filter_by(code=app_code).scalar()
        if not app:
            raise LegacyClientError("app with code({}) does not exists".format(app_code))

        session.add(
            LAppDevelopTimeRecored(
                app_id=app.id,
                dev_time=hours,
                # creater is NOT a typo in current source code but a typo in legacy database
                creater=creator,
                record_time=datetime.datetime.now(),
            )
        )
        # Sum the dev time records and update the "dev_time" field of App model
        total_hours_from_groups = (
            session.query(func.sum(LAppDevelopTimeRecored.dev_time)).filter_by(app_id=app.id).scalar()
        )
        # "dev_time" field in legacy database is text type, we should use round the float value to
        # reserve only the last 2 digits.
        session.query(LApplication).filter_by(id=app.id).update(
            {
                "dev_time": str(round(total_hours_from_groups, 2)),
            }
        )


def get_app_dev_time(app_code) -> float:
    """Get the total app dev time of an app

    :param app_id: the code of Application object
    """
    with console_db.session_scope() as session:
        app = session.query(LApplication).filter_by(code=app_code).scalar()
        if not app:
            raise LegacyClientError("app with code({}) does not exists".format(app_code))
        try:
            return float(app.dev_time)
        except ValueError:
            return 0
