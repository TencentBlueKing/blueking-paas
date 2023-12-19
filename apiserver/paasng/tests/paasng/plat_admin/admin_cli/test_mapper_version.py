import pytest

from paas_wl.bk_app.applications.models.config import Config
from paasng.plat_admin.admin_cli.mapper_version import get_mapper_v1_envs

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class Test__get_mapper_v1_envs:
    def test_normal(self, bk_stag_env):
        assert len(list(get_mapper_v1_envs())) == 0

        # Update existent config object
        c = bk_stag_env.wl_app.latest_config
        c.metadata = {"mapper_version": "v1"}
        c.save()
        assert len(list(get_mapper_v1_envs())) == 1

    def test_multiple_configs(self, bk_stag_env):
        Config.objects.create(app_id=bk_stag_env.wl_app.uuid, metadata={"mapper_version": "v1"})
        assert len(list(get_mapper_v1_envs())) == 1

        # Newer config should override the mapper version value
        Config.objects.create(app_id=bk_stag_env.wl_app.uuid, metadata={"mapper_version": "v2"})
        assert len(list(get_mapper_v1_envs())) == 0
