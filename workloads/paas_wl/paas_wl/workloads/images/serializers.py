# -*- coding: utf-8 -*-
from rest_framework import serializers

from paas_wl.workloads.images.models import AppUserCredential


class AppImageCredentialSerializer(serializers.Serializer):
    """Serializer for Creating AppImageCredential"""

    registry = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField()


class UsernamePasswordPairSLZ(serializers.ModelSerializer):
    """Serializer for username password pair"""

    application_id = serializers.UUIDField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    updated = serializers.DateTimeField(read_only=True)
    password = serializers.CharField(write_only=True)
    description = serializers.CharField(allow_blank=True)

    class Meta:
        model = AppUserCredential
        fields = '__all__'
