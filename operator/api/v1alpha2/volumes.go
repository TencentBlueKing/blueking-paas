/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package v1alpha2

import (
	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/util/validation"
)

// VolumeSource 参考 k8s.io/api/core/v1.VolumeSource
type VolumeSource struct {
	ConfigMap *ConfigMapSource `json:"configMap"`
}

// ToValidator 将 volume source 转换成 VolumeSourceValidator
func (vs *VolumeSource) ToValidator() (VolumeSourceValidator, error) {
	if vs.ConfigMap != nil {
		return vs.ConfigMap, nil
	}
	return nil, errors.New("unknown volume source")
}

// VolumeSourceValidator 接口
// +k8s:deepcopy-gen=false
type VolumeSourceValidator interface {
	// Validate source
	Validate() []string
}

// ConfigMapSource represents a configMap that should populate this volume
type ConfigMapSource struct {
	Name string `json:"name"`
}

// Validate ConfigMap name
func (c ConfigMapSource) Validate() []string {
	return validation.IsDNS1123Subdomain(c.Name)
}

var _ VolumeSourceValidator = new(ConfigMapSource)
