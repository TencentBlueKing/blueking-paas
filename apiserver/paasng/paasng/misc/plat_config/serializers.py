from rest_framework import serializers


class EncryptConfigSLZ(serializers.Serializer):
    enabled = serializers.BooleanField(help_text="是否启用前端加密")
    public_key = serializers.CharField()
    encrypt_field_prefix = serializers.CharField(help_text="加密的字段前缀, 用于区分字段值是否被加密过")
    encrypt_cipher_type = serializers.CharField()
