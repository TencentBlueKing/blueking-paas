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
# Generated by Django 2.2.17 on 2020-12-10 10:08

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppDomainCert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('region', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=128, unique=True, validators=[django.core.validators.RegexValidator('^[a-zA-Z0-9-_]{1,}$')])),
                ('cert_data', models.TextField()),
                ('key_data', models.TextField()),
            ],
            options={
                'abstract': False,
                'db_table': 'services_appdomaincert',
            },
        ),
        migrations.CreateModel(
            name='AppDomainSharedCert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('region', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=128, unique=True, validators=[django.core.validators.RegexValidator('^[a-zA-Z0-9-_]{1,}$')])),
                ('cert_data', models.TextField()),
                ('key_data', models.TextField()),
                ('auto_match_cns', models.TextField(max_length=2048)),
            ],
            options={
                'abstract': False,
                'db_table': 'services_appdomainsharedcert',
            },
        ),
        migrations.CreateModel(
            name='AppDomain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('region', models.CharField(max_length=32)),
                ('host', models.CharField(max_length=128)),
                ('https_enabled', models.BooleanField(default=False)),
                ('https_auto_redirection', models.BooleanField(default=False)),
                ('source', models.IntegerField(choices=[(1, 'BUILT_IN'), (2, 'CUSTOM'), (3, 'INDEPENDENT')])),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.App')),
                ('cert', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='ingress.AppDomainCert')),
                ('shared_cert', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='ingress.AppDomainSharedCert')),
            ],
            options={
                'unique_together': {('region', 'host')},
                'db_table': 'services_appdomain',
            },
        ),
    ]
