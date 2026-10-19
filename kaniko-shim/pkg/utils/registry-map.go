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
	"strings"

	"github.com/pkg/errors"
)

// ParseRegistryMap parses registry maps joined with ',', each item is in format `<registry>=<prefix>`,
// e.g. `mirrors.example.com=registry-proxy.example.com/mirrors-example-com`.
// An invalid item will cause an error instead of being ignored, because a missing map makes kaniko
// pull images from the original registry.
func ParseRegistryMap(registryMap string) ([]string, error) {
	if registryMap == "" {
		return nil, nil
	}

	items := strings.Split(registryMap, ",")
	for _, item := range items {
		// kaniko splits the value of `--registry-map` by ';' again, so it is not allowed here
		if strings.ContainsAny(item, "; \t\r\n") {
			return nil, errors.Errorf("invalid registry map %q: must not contain ';' or whitespace", item)
		}
		registry, prefix, found := strings.Cut(item, "=")
		if !found || registry == "" || prefix == "" || strings.Contains(prefix, "=") {
			return nil, errors.Errorf("invalid registry map %q: expected format is '<registry>=<prefix>'", item)
		}
		if strings.Contains(item, "://") {
			return nil, errors.Errorf("invalid registry map %q: must not contain scheme", item)
		}
	}
	return items, nil
}
