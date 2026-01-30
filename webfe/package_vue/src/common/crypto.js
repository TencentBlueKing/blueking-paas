/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

/**
 * 国密加密工具函数
 */
import { SM2, helper } from '@blueking/crypto-js-sdk';

/**
 * SM2 加密
 * @param {string} msg - 待加密的明文
 * @param {string} publicKey - SM2 公钥 (PEM 格式)
 * @returns {string} Base64 编码的密文
 */
export function sm2Encrypt(msg, publicKey) {
  const sm2 = new SM2();
  const pkey = helper.asn1.decode(publicKey);
  const cipher = sm2.encrypt(pkey, helper.encode.strToHex(msg));
  const base64Ret = helper.encode.hexToBase64(cipher);
  return base64Ret;
}

/**
 * 加密字符串, 并根据加密配置决定是否加密
 * 约定字符串经过加密后, 变为 object: { _encrypted: true, _encrypted_value: 'Base64 encode hex ciphertext'}
 * @param {string} str - 待加密的字符串
 * @param {Object} encryptConfig - 加密配置 { enabled: boolean, public_key: string }
 * @returns {Object|string} 加密后的数据(object)或原字符串
 */
export function encryptString(str, encryptConfig) {
  if (encryptConfig?.enabled && str) {
    const encryptedValue = sm2Encrypt(str, encryptConfig.public_key);
    return {
      _encrypted: true,
      _encrypted_value: encryptedValue,
    };
  }
  return str;
}
