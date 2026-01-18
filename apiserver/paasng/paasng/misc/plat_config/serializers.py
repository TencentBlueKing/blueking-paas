from rest_framework import serializers


class EncryptConfigInputSLZ(serializers.Serializer):
    public_key = serializers.CharField(allow_null=True)
    encrypt_cipher_type = serializers.ChoiceField(allow_null=True, choices=["SM2"], help_text="加密算法类型")
