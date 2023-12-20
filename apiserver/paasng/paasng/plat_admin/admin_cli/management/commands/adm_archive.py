"""An admin tool that helps archive applications."""
from typing import List

from django.core.management.base import BaseCommand

from paasng.plat_admin.admin_cli.cmd_utils import CommandBasicMixin
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.deploy.archive import start_archive_step
from paasng.platform.engine.exceptions import OfflineOperationExistError
from paasng.platform.engine.utils.query import DeploymentGetter


class Command(BaseCommand, CommandBasicMixin):
    help = "This command archives applications."

    def add_arguments(self, parser):
        parser.add_argument("--app-ids", required=True, type=str, nargs="+", help="The application ids")

    def handle(self, *args, **options):
        for app_id in options["app_ids"]:
            self._archive_app_id(app_id)

    def _archive_app_id(self, app_id: str):
        """Archive an application by app id."""
        try:
            app = Application.objects.get(code=app_id)
        except Application.DoesNotExist:
            self.print(f"Application {app_id} not found.")
            return

        self.print(f"# Archive application {app.code}, name: {app.name}, created by {app.creator.username}.")
        self.print("# Environments:")
        deployed_envs: List[ModuleEnvironment] = []
        for env in app.envs.all():
            if deploy := DeploymentGetter(env).get_latest_succeeded():
                deployed_status = "Deployed at {}".format(deploy.created.strftime("%Y-%m-%d %H:%M"))
                deployed_envs.append(env)
            else:
                deployed_status = "(not deployed)"
            print("{:16} {:8} {}".format(env.module.name, env.environment, deployed_status))

        if not deployed_envs:
            self.print("No deployed environments, skipped.")
            return

        # Archive all deployed environments
        if input("Will archive all DEPLOYED environments, are you sure? (yes/y/no/n) ").lower() not in {"y", "yes"}:
            self.print("Skipped.")
            return

        for env in deployed_envs:
            title = f"{app.code}: {env.module.name}/{env.environment}"
            try:
                self.print("Start archiving, please wait...", title)
                start_archive_step(env, operator=app.creator)
            except OfflineOperationExistError:
                self.print("Archiving is already in progress, check later.", title)
            except Exception as e:
                self.print(f"Unknown error when archiving, err: {e}", title)
            else:
                self.print("Archive finished")
