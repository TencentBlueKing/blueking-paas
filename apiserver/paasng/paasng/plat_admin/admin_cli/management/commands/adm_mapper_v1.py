"""An admin tool that helps migrate applications that using resource mapper v1 to v2.

# 使用说明：

首先，查询当前正在使用 resource mapper v1 版本的应用环境列表：

    python manage.py adm_stats --type res_mapper_v1

在列表中挑选一个环境，后续需使用其 EnvID 字段。执行命令将该环境升级为使用 resource mapper v2 版本：

    python manage.py adm_mapper_v1 --action upgrade --env-id {ENV_ID}

命令将部署新的 v2 版本的资源并将用户访问指向到新资源。

验证该环境的相关功能是否正常，如果正常，执行下面的命令删除旧的 v1 版本的集群资源来完成升级：

    python manage.py adm_mapper_v1 --action clean_v1 --env-id {ENV_ID}

如在验证时发现异常，可使用以下命令将环境回滚为升级前的 v1 版本：

    python manage.py adm_mapper_v1 --action rollback --env-id {ENV_ID}

"""
import sys
from enum import Enum

from django.core.management.base import BaseCommand

from paas_wl.bk_app.applications.api import get_latest_build_id
from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata, update_metadata
from paas_wl.bk_app.applications.models.release import Release
from paas_wl.bk_app.deploy.app_res.utils import get_scheduler_client_by_app
from paasng.plat_admin.admin_cli.cmd_utils import CommandBasicMixin
from paasng.plat_admin.admin_cli.deploy import list_proc_types, refresh_services, wait_for_release
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.deploy.release.legacy import release_by_engine


class CommandAction(str, Enum):
    """A command action."""

    # Upgrade to resource mapper v2
    UPGRADE = "upgrade"
    # Rollback to resource mapper v1
    ROLLBACK = "rollback"
    # Clean up the resources owned by v1
    CLEAN_V1 = "clean_v1"


SUPPORTED_ACTIONS = [opt.value for opt in CommandAction]


class Command(BaseCommand, CommandBasicMixin):
    help = "This command helps migrate applications that use the v1 resource mapper rule."

    def add_arguments(self, parser):
        parser.add_argument("--action", choices=SUPPORTED_ACTIONS, required=True, type=str, help="Command action")
        parser.add_argument("--env-id", type=str, required=True, help="The ID of environment")

    def handle(self, *args, **options):
        try:
            env = ModuleEnvironment.objects.get(id=options["env_id"])
        except ModuleEnvironment.DoesNotExist:
            self.exit_with_error(f"Environment {options['env_id']} does not exist")

        if options["action"] == CommandAction.UPGRADE.value:
            self._handle_upgrade(env)
        elif options["action"] == CommandAction.ROLLBACK.value:
            self._handle_rollback(env)
        elif options["action"] == CommandAction.CLEAN_V1.value:
            self._handle_clean_v1(env)
        else:
            raise RuntimeError("Invalid action")

    def _handle_upgrade(self, env: ModuleEnvironment):
        """Upgrade the environment to use resource mapper v2, it will re-deploy the environment
        and forward all requests to the new workload resources.
        """
        self.print("Upgrade the environment to use resource mapper v2.")
        wl_app = env.wl_app
        if get_metadata(wl_app).mapper_version == "v2":
            self.print("Already using mapper v2, exit.")
            return

        update_metadata(wl_app, mapper_version="v2")
        try:
            self._upgrade_env(env)
        except Exception as e:
            self.print(f"Error upgrading: {e}, restore mapper version to v1.")
            update_metadata(wl_app, mapper_version="v1")

    def _upgrade_env(self, env: ModuleEnvironment):
        """
        :raise ValueError: when upgrade failed
        """
        # Create a new release using the mapper v2 and the latest build
        build = get_latest_build_id(env)
        if not build:
            raise RuntimeError("No build found")

        release_id = release_by_engine(env, str(build))
        release = Release.objects.get(pk=release_id)
        self.print(f"Created new release using mapper v2: {release_id}, version: {release.version}")

        self.print("Waiting for the release to become ready...")

        def _interval_cb():
            """Animation: print a "." periodically"""
            sys.stdout.write(".")
            sys.stdout.flush()

        if not wait_for_release(release, timeout_seconds=300, interval_callback=_interval_cb):
            self.print("Timeout, release is still not ready, something might be wrong, try again later.")
            raise RuntimeError("Release timeout")
        else:
            self.print("Done")

        self.print("Refreshing service resources, requests will be forwarded to new workloads...")
        refresh_services(env)
        self.print("Upgrade finished, please verify.")

    def _handle_rollback(self, env: ModuleEnvironment):
        """Rollback an environment to use mapper v1, it WON'T re-deploy the environment."""
        wl_app = env.wl_app

        self.print("Remove the workloads deployed using mapper v2.")
        s_client = get_scheduler_client_by_app(env.wl_app)
        for proc_type in list_proc_types(env):
            self.print(f"Deleting process: {proc_type}...")
            s_client.processes_handler.delete_gracefully(wl_app, proc_type)

        # TODO: Check if v1 workload resources are still there, if not, report error and quit.
        self.print("Refreshing service resources, requests will be forwarded to older workloads...")
        update_metadata(wl_app, mapper_version="v1")
        refresh_services(env)
        self.print("Rollback finished.")

    def _handle_clean_v1(self, env: ModuleEnvironment):
        """Remove the workloads deployed using mapper v1."""
        wl_app = env.wl_app
        old_version = get_metadata(wl_app).mapper_version

        # Set the mapper_version to perform deletion, the value will be restored in the end.
        update_metadata(wl_app, mapper_version="v1")
        self.print("Remove the workloads deployed using mapper v1.")
        try:
            s_client = get_scheduler_client_by_app(env.wl_app)
            for proc_type in list_proc_types(env):
                self.print(f"Deleting process: {proc_type}...")
                s_client.processes_handler.delete_gracefully(wl_app, proc_type)
        finally:
            update_metadata(wl_app, mapper_version=old_version)
