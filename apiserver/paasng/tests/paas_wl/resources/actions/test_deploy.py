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
import pytest

from paas_wl.resources.actions.deploy import ZombieProcessesKiller
from tests.paas_wl.utils.wl_app import release_setup

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestZombieProcessesKiller:
    @pytest.mark.parametrize(
        "last_procfile,latest_procfile,diff",
        [
            ({"web": "command -x -z -y"}, {"web1": "command -x -z -y"}, {"types": ["web"], "names": []}),
            (
                {"web": "command -x -z -y", "web1": "command -x -z -y"},
                {"web": "command2 -x -z -y"},
                {"types": ["web1"], "names": ["web"]},
            ),
            (
                {"web": "command -x -z -y", "web1": "command -x -z -y"},
                {"web": "command2 -x -z -y", "web1": "command3 -x -z -y"},
                {"types": [], "names": ["web", "web1"]},
            ),
            (
                {
                    'web': 'gunicorn1 wsgi -w 4 -b :$PORT --access-logfile - '
                    '--error-logfile - --access-logformat \'[%(h)s] '
                    '%({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
                },
                {
                    'web': 'gunicorn wsgi -w 4 -b :$PORT --access-logfile - '
                    '--error-logfile - --access-logformat \'[%(h)s] '
                    '%({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
                },
                {"types": [], "names": ["web"]},
            ),
            (
                {"web": "command -x -z -y", "web1": "command -x -z -y"},
                {"web": "command -x -z -y", "web1": "command -x -z -y"},
                {"types": [], "names": []},
            ),
            (
                {"web": "command -x -z -y", "web1": "command -x -z -y"},
                {"web2": "command -x -z -y", "web3": "command -x -z -y"},
                {"types": ["web", "web1"], "names": []},
            ),
        ],
    )
    def test_search(self, wl_app, latest_procfile, last_procfile, diff):
        last_release = release_setup(wl_app, build_params={"procfile": last_procfile})
        latest_release = release_setup(
            wl_app,
            build_params={"procfile": latest_procfile},
            release_params={"version": last_release.version + 1},
        )

        killer = ZombieProcessesKiller(release=latest_release, last_release=last_release)
        types, names = killer.search()

        assert len(types) == len(diff["types"])
        assert len(names) == len(diff["names"])

        assert {x.name for x in types} == set(diff["types"])
        assert {x.name for x in names} == set(diff["names"])
