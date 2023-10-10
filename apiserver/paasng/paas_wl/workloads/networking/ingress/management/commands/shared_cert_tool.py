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
"""A tool for managing shared tls certifications
"""
# TODO: Remove this script, it has been replaced by the functions in admin dashboard.
import argparse
import logging
import sys

from django.core.management.base import BaseCommand

from paas_wl.workloads.networking.ingress.models import AppDomainSharedCert
from paas_wl.workloads.networking.ingress.serializers import AppDomainSharedCertSLZ
from paas_wl.utils.views import one_line_error

logger = logging.getLogger("commands")

ACTION_CREATE = 'create'
ACTION_UPDATE = 'update'
ENABLED_ACTIONS = [ACTION_CREATE, ACTION_UPDATE]


class Command(BaseCommand):
    """This command can do below things:

    - create: Create a new shared certification
    - update: Update a shared certification
    """

    help = 'Managing shared tls certifications'

    def add_arguments(self, parser):
        parser.add_argument("--action", choices=ENABLED_ACTIONS, required=True, type=str, help="Name of action")
        parser.add_argument("--name", type=str, required=True, help="Name of certification object")
        parser.add_argument("--cert-path", type=argparse.FileType('r'), required=True, help="Path of cert file")
        parser.add_argument("--key-path", type=argparse.FileType('r'), required=True, help="Path of private key file")
        parser.add_argument("--auto-match-cns", type=str, required=False, help="Auto match CN")

        # Arguments for create action only
        parser.add_argument("--region", type=str, required=False, help="region of certification, required for create")
        parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")

    def handle(self, *args, **options):
        if options['action'] == ACTION_CREATE:
            return self.handle_create(options)
        elif options['action'] == ACTION_UPDATE:
            return self.handle_update(options)
        else:
            raise RuntimeError('Invalid action')

    @staticmethod
    def exit_with_error(message: str, code: int = 2):
        """Exit execution with error message"""
        logger.error('Error: %s', message)
        sys.exit(2)

    def handle_create(self, options):
        """Handle create action"""
        if options['dry_run']:
            self.exit_with_error('create action does not support dry run mode')
        if not options.get('region'):
            self.exit_with_error('"--region" is required for creation')

        name = options['name']
        slz = AppDomainSharedCertSLZ(
            data={
                'region': options['region'],
                'name': name,
                'cert_data': options['cert_path'].read(),
                'key_data': options['key_path'].read(),
                'auto_match_cns': options.get('auto_match_cns', ''),
            }
        )
        # Validate input using serializer
        if not slz.is_valid():
            logger.error('Argument error: %s', one_line_error(slz.errors))
            return

        logger.info('Creating shared cert: %s', name)
        slz.save()

    def handle_update(self, options):
        """Handle update action"""
        name = options['name']
        try:
            cert = AppDomainSharedCert.objects.get(name=name)
        except AppDomainSharedCert.DoesNotExist:
            self.exit_with_error(f'cert "{name}" does not exist')

        # Forbid modifying common names
        auto_match_cns = options.get('auto_match_cns', '')
        if auto_match_cns and auto_match_cns != cert.auto_match_cns:
            self.exit_with_error(
                f'modifying auto match CN is not supported yet, the original CN is "{cert.auto_match_cns}""'
            )

        logger.info('Modifying shared cert object...')
        if options['dry_run']:
            logger.info('(dry-run mode) skipping updating...')
        else:
            cert.cert_data = options['cert_path'].read()
            cert.key_data = options['key_path'].read()
            cert.save()

        logger.info('Certificate updated.')
        logger.info('Run "refresh_cert" command to fresh related resources.')
        return
