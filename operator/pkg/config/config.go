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

// Package config provides project config
package config

// ProjectConfigReader is an interface for reading project config, it is used to
// avoid import "paasv1alpha1" package from here so that import cycle will not happen.
type ProjectConfigReader interface {
	// Process related methods
	GetMaxProcesses() int32
	GetProcMaxReplicas() int32
	GetProcDefaultCpuLimit() string
	GetProcDefaultMemLimit() string
	GetProcDefaultCpuRequest() string
	GetProcDefaultMemRequest() string

	// Platform related methods
	GetIngressClassName() string
	// GetCustomDomainIngressClassName returns the ingress class name for custom domain ingress
	GetCustomDomainIngressClassName() string
	IsAutoscalingEnabled() bool
}

// defaultConfig is a default implementation of ProjectConfigReader, it will be used
// as the default config if no other configs is set.
type defaultConfig struct{}

func (d defaultConfig) GetMaxProcesses() int32 {
	return 8
}

func (d defaultConfig) GetProcMaxReplicas() int32 {
	return 5
}

func (d defaultConfig) GetProcDefaultCpuLimit() string {
	return "4"
}

func (d defaultConfig) GetProcDefaultMemLimit() string {
	return "1Gi"
}

func (d defaultConfig) GetProcDefaultCpuRequest() string {
	return ""
}

func (d defaultConfig) GetProcDefaultMemRequest() string {
	return ""
}

func (d defaultConfig) GetIngressClassName() string {
	return "nginx"
}

// GetCustomDomainIngressClassName returns the ingress class name for custom domain ingress
func (d defaultConfig) GetCustomDomainIngressClassName() string {
	return d.GetIngressClassName()
}

func (d defaultConfig) IsAutoscalingEnabled() bool {
	return false
}

// Global global config instance
var Global ProjectConfigReader = defaultConfig{}

// SetConfig will set the Global by given cfg
func SetConfig(cfg ProjectConfigReader) {
	Global = cfg
}
