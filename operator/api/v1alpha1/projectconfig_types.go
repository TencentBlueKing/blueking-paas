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

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	cfg "sigs.k8s.io/controller-runtime/pkg/config/v1alpha1"
)

// PlatformConfig contains the config for interacting with other service
type PlatformConfig struct {
	// Authentication information for calling BlueKing APIs (components, BkOAuth services, etc.)
	BkAppCode   string `json:"bkAppCode"`
	BkAppSecret string `json:"bkAppSecret"`
	// BlueKing's component API address, the gateway SDK depends on this configuration
	BkAPIGatewayURL string `json:"bkAPIGatewayURL"`
	// sentry server dsn, all events waiting for report will be dropped if unset
	SentryDSN string `json:"sentryDSN"`
	// if ingressClassName configured, kubernetes.io/ingress.class=$value will be added to ingress's annotations
	IngressClassName string `json:"ingressClassName"`
}

// IngressPluginConfig contains the config for controlling ingress config
type IngressPluginConfig struct {
	AccessControlConfig *AccessControlConfig `json:"accessControlConfig,omitempty"`
}

// AccessControlConfig contains the config for controlling ingress snippet about Access control module
type AccessControlConfig struct {
	// bk-ingress-nginx choose which redis key to connect to, optional values 'prod', 'test', 'local'
	RedisConfigKey string `json:"redisConfigKey"`
}

// ResLimitConfig contains bkapp resource limit
type ResLimitConfig struct {
	// ProcDefaultCPULimits is process's default cpu quota
	ProcDefaultCPULimits string `json:"procDefaultCPULimits"`

	// ProcDefaultMemLimits is process's default memory quota
	ProcDefaultMemLimits string `json:"procDefaultMemLimits"`

	// MaxReplicas is single instance max replica num
	MaxReplicas int32 `json:"maxReplicas"`
}

//+kubebuilder:object:root=true

// ProjectConfig is the Schema for the project configs API
type ProjectConfig struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	// ControllerManagerConfigurationSpec returns the configurations for controllers
	cfg.ControllerManagerConfigurationSpec `json:",inline"`

	PlatformConfig      PlatformConfig      `json:"platformConfig"`
	IngressPluginConfig IngressPluginConfig `json:"ingressPluginConfig"`
	ResLimitConfig      ResLimitConfig      `json:"resLimitConfig"`
}

// NewProjectConfig create project config
func NewProjectConfig() *ProjectConfig {
	conf := ProjectConfig{}

	// worker 数量默认为 5
	conf.Controller = &cfg.ControllerConfigurationSpec{
		GroupKindConcurrency: map[string]int{
			GroupKindBkApp.String():              5,
			GroupKindDomainGroupMapping.String(): 5,
		},
	}

	// 资源预设默认值
	conf.ResLimitConfig.ProcDefaultCPULimits = "4000m"
	conf.ResLimitConfig.ProcDefaultMemLimits = "1024Mi"
	conf.ResLimitConfig.MaxReplicas = 5

	return &conf
}

func init() {
	SchemeBuilder.Register(&ProjectConfig{})
}
