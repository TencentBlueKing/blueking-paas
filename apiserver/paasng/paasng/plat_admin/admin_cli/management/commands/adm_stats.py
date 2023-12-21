"""An admin tool that helps viewing platform and application stats."""
import logging
from enum import Enum
from operator import attrgetter

from django.core.management.base import BaseCommand

from paasng.plat_admin.admin_cli.cmd_utils import CommandBasicMixin
from paasng.plat_admin.admin_cli.mapper_version import get_mapper_v1_envs

logger = logging.getLogger("commands")


class CommandType(Enum):
    # Show applications that still use the resource mapper "v1"(legacy)
    RES_MAPPER_V1 = "res_mapper_v1"


SUPPORTED_TYPES = [t.value for t in CommandType]


class Command(BaseCommand, CommandBasicMixin):
    help = "This command supports viewing different kinds of stats."

    def add_arguments(self, parser):
        parser.add_argument("--type", choices=SUPPORTED_TYPES, required=True, type=str, help="Command type.")

    def handle(self, *args, **options):
        if options["type"] == CommandType.RES_MAPPER_V1.value:
            self.handle_res_mapper_v1(options)
        else:
            self.exit_with_error(f'Invalid command type: {options["type"]}')

    def handle_res_mapper_v1(self, options):
        """Print applications that still use resource mapper "v1" version."""
        envs = list(get_mapper_v1_envs())
        self.print(f"== Found {len(envs)} environments that uses resource mapper v1 ==")
        if not envs:
            return

        # Print table header
        cols_placeholder = "{:<12} {:16} {:12} {:8} {:16} {}"
        self.print(cols_placeholder.format("EnvId", "AppId", "ModuleName", "EnvName", "Creator", "LastDeployed"))
        # Print table data
        for env in sorted(envs, key=attrgetter("id")):
            app = env.application
            module = env.module
            col = cols_placeholder.format(
                env.id,
                app.code,
                module.name,
                env.environment,
                app.creator.username,
                app.last_deployed_date.strftime("%Y-%m-%d %H:%M") if app.last_deployed_date else "",
            )
            self.print(col)
