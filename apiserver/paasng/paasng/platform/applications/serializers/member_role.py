# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.constants import ApplicationRole
from paasng.utils.serializers import UserField


class RoleField(serializers.Field):
    """Role field for present role object friendly"""

    def to_representation(self, value):
        return {'id': value, 'name': ApplicationRole(value).name.lower()}

    def to_internal_value(self, data):
        try:
            role_id = data['id']
        except Exception:
            raise ValidationError('Incorrect role param. Expected like {role: {"id": 3}}.')
        try:
            ApplicationRole(role_id)
        except Exception:
            raise ValidationError(_("%s 不是合法选项") % role_id)
        return role_id


class ApplicationMemberSLZ(serializers.Serializer):
    user = UserField()
    roles = serializers.ListField(child=RoleField(), help_text='用户角色列表')


class ApplicationMemberRoleOnlySLZ(serializers.Serializer):
    """Serializer for update, only role"""

    role = RoleField()
