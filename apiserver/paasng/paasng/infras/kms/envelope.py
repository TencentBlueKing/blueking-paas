# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""KMS 混合加密信封

算法组合由 KMS 部署配置决定，通过 get_crypto_info 下发：非对称 RSA / SM2 × 对称 AES / SM4 × 模式 CBC / CTR。
每次加密生成新的随机 16 字节对称密钥与 IV：
- encrypted_key：RSA-OAEP(SHA-256, MGF1-SHA-256, 空 label) 或 SM2（ASN.1 密文）包装的对称密钥
- ciphertext：IV || 对称加密结果。CBC 使用 PKCS#7 填充，CTR 不填充
- 信封 JSON 整体做标准 Base64，结果填入凭证的 metadata.value

格式与 bk-kms-sdk 的解密实现保持一致。
"""

import base64
import json
import secrets
from dataclasses import dataclass

from bkcrypto.asymmetric.ciphers.sm2 import SM2AsymmetricCipher
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .constants import SYMMETRIC_BLOCK_BYTES, SYMMETRIC_KEY_BYTES
from .exceptions import KMSCryptoError, KMSValidationError

_SYMMETRIC_ALGORITHMS = {"AES": algorithms.AES, "SM4": algorithms.SM4}
_SYMMETRIC_MODES = frozenset({"CBC", "CTR"})


@dataclass(frozen=True)
class CryptoInfo:
    """get_crypto_info 返回的加密信息"""

    asymmetric_type: str
    symmetric_type: str
    symmetric_mode: str
    # Base64 编码后的 PEM 公钥
    public_key: str


def hybrid_encrypt(plaintext: str, crypto: CryptoInfo) -> str:
    """对明文做混合加密，返回可直接填入 metadata.value 的字符串

    :raises KMSCryptoError: 服务端下发的算法不受支持，或公钥与算法不匹配
    :raises KMSValidationError: 明文无法按 UTF-8 编码
    """
    algorithm = _SYMMETRIC_ALGORITHMS.get(crypto.symmetric_type)
    if (
        algorithm is None
        or crypto.symmetric_mode not in _SYMMETRIC_MODES
        or crypto.asymmetric_type not in ("RSA", "SM2")
    ):
        suite = (crypto.asymmetric_type, crypto.symmetric_type, crypto.symmetric_mode)
        raise KMSCryptoError(f"unsupported crypto suite from KMS: {suite}")
    public_key_pem = _decode_public_key(crypto.public_key)

    try:
        raw = plaintext.encode("utf-8")
    except UnicodeEncodeError as e:
        raise KMSValidationError("plaintext must be valid UTF-8 text") from e

    symmetric_key = secrets.token_bytes(SYMMETRIC_KEY_BYTES)
    iv = secrets.token_bytes(SYMMETRIC_BLOCK_BYTES)
    if crypto.symmetric_mode == "CBC":
        padder = sym_padding.PKCS7(SYMMETRIC_BLOCK_BYTES * 8).padder()
        raw = padder.update(raw) + padder.finalize()
        encryptor = Cipher(algorithm(symmetric_key), modes.CBC(iv)).encryptor()
    else:
        encryptor = Cipher(algorithm(symmetric_key), modes.CTR(iv)).encryptor()
    ciphertext = encryptor.update(raw) + encryptor.finalize()

    if crypto.asymmetric_type == "SM2":
        encrypted_key = _sm2_wrap(public_key_pem, symmetric_key)
    else:
        encrypted_key = _rsa_wrap(public_key_pem, symmetric_key)

    envelope = {
        "asymmetric_type": crypto.asymmetric_type,
        "symmetric_type": crypto.symmetric_type,
        "symmetric_mode": crypto.symmetric_mode,
        "encrypted_key": encrypted_key,
        "ciphertext": _b64encode(iv + ciphertext),
    }
    return _b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8"))


def _decode_public_key(public_key_b64: str) -> bytes:
    try:
        return base64.b64decode(public_key_b64, validate=True)
    except ValueError as e:
        raise KMSCryptoError("KMS public key is not valid Base64") from e


def _rsa_wrap(public_key_pem: bytes, symmetric_key: bytes) -> str:
    try:
        key = serialization.load_pem_public_key(public_key_pem)
    except (ValueError, TypeError, UnsupportedAlgorithm) as e:
        raise KMSCryptoError("KMS public key is not a valid PEM") from e
    if not isinstance(key, rsa.RSAPublicKey):
        raise KMSCryptoError("KMS public key is not an RSA key")

    try:
        encrypted_key = key.encrypt(
            symmetric_key,
            asym_padding.OAEP(mgf=asym_padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
    except ValueError as e:
        raise KMSCryptoError("failed to wrap the symmetric key with the KMS public key") from e
    return _b64encode(encrypted_key)


def _sm2_wrap(public_key_pem: bytes, symmetric_key: bytes) -> str:
    """bkcrypto 输出 Base64 编码的 ASN.1 密文，与 SDK 中 decrypt_bytes 的输入格式一致"""
    try:
        cipher = SM2AsymmetricCipher(public_key_string=public_key_pem.decode("utf-8"))
        return cipher.encrypt_bytes(symmetric_key)
    except Exception as e:
        raise KMSCryptoError("failed to wrap the symmetric key with the KMS SM2 public key") from e


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
