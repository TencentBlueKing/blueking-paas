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
package utils

import (
	"encoding/base64"
	"strings"
)

// ParseBuildArgs will parse an encoded string
// the string
func ParseBuildArgs(buildArgs string) (decodedArgs []string, err error) {
	if buildArgs == "" {
		return nil, nil
	}
	parts := strings.Split(buildArgs, ",")

	for _, encoded := range parts {
		plaintext, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil {
			return nil, err
		}
		decodedArgs = append(decodedArgs, string(plaintext))
	}
	return decodedArgs, nil
}
