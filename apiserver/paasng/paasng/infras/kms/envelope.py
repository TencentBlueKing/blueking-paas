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

按 KMS 管理接口文档实现：每次加密生成新的随机 16 字节 AES 密钥与 IV。
- encrypted_key：RSA-OAEP(SHA-256, MGF1-SHA-256, 空 label) 包装的 AES 密钥
- ciphertext：IV || AES-128-CBC(PKCS#7(明文))
- 信封 JSON 整体做标准 Base64，结果填入凭证的 metadata.value

与官方 bk-kms-sdk 的解密规则一致：OAEP 使用 SHA-256 与 MGF1-SHA-256、空 label；CBC 前 16 字节为 IV；
PKCS#7 严格校验。
"""

import base64
import json
import secrets
from dataclasses import dataclass

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .constants import AES_BLOCK_BITS, AES_BLOCK_BYTES, AES_KEY_BYTES, SUPPORTED_CRYPTO_SUITE
from .exceptions import KMSCryptoError, KMSValidationError


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

    :raises KMSCryptoError: 服务端下发的算法不受支持，或公钥不是可用的 RSA 公钥
    :raises KMSValidationError: 明文无法按 UTF-8 编码
    """
    suite = (crypto.asymmetric_type, crypto.symmetric_type, crypto.symmetric_mode)
    if suite != SUPPORTED_CRYPTO_SUITE:
        raise KMSCryptoError(f"unsupported crypto suite from KMS: {suite}")
    public_key = _load_rsa_public_key(crypto.public_key)

    try:
        raw = plaintext.encode("utf-8")
    except UnicodeEncodeError as e:
        raise KMSValidationError("plaintext must be valid UTF-8 text") from e

    # 每次加密都使用新的对称密钥与 IV，不复用
    symmetric_key = secrets.token_bytes(AES_KEY_BYTES)
    iv = secrets.token_bytes(AES_BLOCK_BYTES)

    padder = sym_padding.PKCS7(AES_BLOCK_BITS).padder()
    padded = padder.update(raw) + padder.finalize()
    encryptor = Cipher(algorithms.AES(symmetric_key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    try:
        encrypted_key = public_key.encrypt(
            symmetric_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except ValueError as e:
        raise KMSCryptoError("failed to wrap the symmetric key with the KMS public key") from e

    envelope = {
        "asymmetric_type": crypto.asymmetric_type,
        "symmetric_type": crypto.symmetric_type,
        "symmetric_mode": crypto.symmetric_mode,
        "encrypted_key": _b64encode(encrypted_key),
        "ciphertext": _b64encode(iv + ciphertext),
    }
    return _b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8"))


def _load_rsa_public_key(public_key_b64: str) -> rsa.RSAPublicKey:
    try:
        pem = base64.b64decode(public_key_b64, validate=True)
        key = serialization.load_pem_public_key(pem)
    except (ValueError, TypeError, UnsupportedAlgorithm) as e:
        raise KMSCryptoError("KMS public key is not a valid Base64 encoded PEM") from e

    if not isinstance(key, rsa.RSAPublicKey):
        raise KMSCryptoError("KMS public key is not an RSA key")
    return key


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
