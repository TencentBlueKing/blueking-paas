# Generated by Django 4.2.17 on 2025-03-06 09:57
"""This migration migrates data from the deprecated models in accounts to the new sysapi_client models."""

import logging

from django.db import migrations
from paasng.infras.sysapi_client.constants import ClientRole

logger = logging.getLogger(__name__)


def forwards_func(apps, schema_editor):
    """Migrate data from the deprecated models in accounts to sysapi_client."""
    _migrate_clients(apps)
    _migrate_private_tokens(apps)
    _migrate_app_as_clients(apps)

def _migrate_clients(apps):
    """Migrate data from accounts.User/UserProfile to sysapi_client.SysAPIClient"""
    LUser = apps.get_model("accounts", "User")
    LUserProfile = apps.get_model("accounts", "UserProfile")
    SysAPIClient = apps.get_model("sysapi_client", "SysAPIClient")

    for profile in LUserProfile.objects.all():
        # Filter only the valid users with system roles
        try:
            role = ClientRole(profile.role)
        except ValueError:
            continue
        if role == ClientRole.NOBODY:
            continue
        try:
            user = LUser.objects.get(username=profile.user.username)
        except LUser.DoesNotExist:
            logger.info("User %s does not exist, skip", profile.user.username)
            continue

        # After the filtering, the `user` should be a system api client
        username = user.username
        _, created = SysAPIClient.objects.get_or_create(
            name=username,
            defaults={"role": role.value, "is_active": user.is_active},
        )
        if created:
            logger.info("Migrated user %s to client", username)
        else:
            logger.info("Client %s already exists, skip", username)

def _migrate_private_tokens(apps):
    """Migrate data from accounts.UserPrivateToken to sysapi_client.ClientPrivateToken"""
    LUserPrivateToken = apps.get_model("accounts", "UserPrivateToken")
    SysAPIClient = apps.get_model("sysapi_client", "SysAPIClient")
    ClientPrivateToken = apps.get_model("sysapi_client", "ClientPrivateToken")

    for token in LUserPrivateToken.objects.all():
        username = token.user.username
        try:
            client = SysAPIClient.objects.get(name=username)
        except SysAPIClient.DoesNotExist:
            logger.info("Client %s does not exist, skip", username)
            continue

        _, created = ClientPrivateToken.objects.get_or_create(
            token=token.token,
            defaults={"client": client, "expires_at": token.expires_at, "is_active": token.is_active},
        )
        if created:
            logger.info("Migrated private token for client %s", client.name)
        else:
            logger.info("A private token with the same value already exists, skip")

def _migrate_app_as_clients(apps):
    """Migrate data from AuthenticatedAppAsUser to AuthenticatedAppAsClient"""
    LAuthenticatedAppAsUser = apps.get_model("accounts", "AuthenticatedAppAsUser")
    SysAPIClient = apps.get_model("sysapi_client", "SysAPIClient")
    AuthenticatedAppAsClient = apps.get_model("sysapi_client", "AuthenticatedAppAsClient")

    for app_as_user in LAuthenticatedAppAsUser.objects.all():
        username = app_as_user.user.username
        try:
            client = SysAPIClient.objects.get(name=username)
        except SysAPIClient.DoesNotExist:
            logger.info("Client %s does not exist, skip", username)
            continue
        
        _, created = AuthenticatedAppAsClient.objects.get_or_create(
            bk_app_code=app_as_user.bk_app_code,
            defaults={"client": client}
        )
        
        if created:
            logger.info("Migrated authenticated app %s <-> %s", app_as_user.bk_app_code, client.name)
        else:
            logger.info("An authenticated app with code %s already exists, skip", app_as_user.bk_app_code)


class Migration(migrations.Migration):
    dependencies = [
        ("sysapi_client", "0001_initial"),
        # Dependent on the legacy private token model
        ("accounts", "0003_privatetokenholder"),
    ]

    operations = [migrations.RunPython(forwards_func)]
