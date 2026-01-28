from rest_framework import serializers


class EncryptConfigOutputSLZ(serializers.Serializer):
    enable_frontend_encrypt = serializers.BooleanField(help_text="是否开启前端加密")
    public_key = serializers.CharField(allow_null=True, help_text="公钥")
    encrypt_cipher_type = serializers.ChoiceField(allow_null=True, choices=["SM2"], help_text="加密算法类型")
