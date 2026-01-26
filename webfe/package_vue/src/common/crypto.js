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
 * 根据加密配置决定是否使用 SM2 加密密码
 * @param {string} password - 待加密的密码
 * @param {Object} encryptConfig - 加密配置 { enabled: boolean, public_key: string }
 * @returns {string} 加密后的密码或原密码
 */
export function getEncryptedPassword(password, encryptConfig) {
  if (encryptConfig?.enabled && password) {
    return sm2Encrypt(password, encryptConfig.public_key);
  }
  return password;
}
