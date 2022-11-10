# -*- coding: utf-8 -*-
import pytest

from paas_wl.resources.actions.deploy import ZombieProcessesKiller
from tests.utils.app import release_setup

pytestmark = pytest.mark.django_db


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
    def test_search(self, fake_app, latest_procfile, last_procfile, diff):
        last_release = release_setup(fake_app, build_params={"procfile": last_procfile})
        latest_release = release_setup(
            fake_app, build_params={"procfile": latest_procfile}, release_params={"version": last_release.version + 1}
        )

        killer = ZombieProcessesKiller(release=latest_release, last_release=last_release)
        types, names = killer.search()

        assert len(types) == len(diff["types"])
        assert len(names) == len(diff["names"])

        assert set([x.name for x in types]) == set(diff["types"])
        assert set([x.name for x in names]) == set(diff["names"])
