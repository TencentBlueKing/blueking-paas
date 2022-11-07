/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
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
	// 调用蓝鲸 API （组件、BkOAuth 服务等）的鉴权信息
	BkAppCode   string `json:"bkAppCode"`
	BkAppSecret string `json:"bkAppSecret"`
	// 蓝鲸的组件 API 地址，网关 SDK 依赖该配置项
	BkAPIGatewayURL string `json:"bkAPIGatewayURL"`
}

// IngressPluginConfig contains the config for controlling ingress config
type IngressPluginConfig struct {
	AccessControlConfig *AccessControlConfig `json:"accessControlConfig,omitempty"`
}

// AccessControlConfig contains the config for controlling ingress snippet about Access control module
type AccessControlConfig struct {
	// bk-ingress-nginx 选择连接哪个 redis 的 key, 可选值 'prod', 'test', 'local'
	RedisConfigKey string `json:"redisConfigKey"`
}

// ExperimentalFeatures is a set of ExperimentalFeature
type ExperimentalFeatures struct {
	// 使用 networkingV1Beta1 下发 Ingress 配置, 适用于 1.16 版本的 k8s 集群
	UseNetworkingV1Beta1 bool `json:"useNetworkingV1Beta1"`
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

	PlatformConfig       PlatformConfig       `json:"platformConfig"`
	IngressPluginConfig  IngressPluginConfig  `json:"ingressPluginConfig"`
	ExperimentalFeatures ExperimentalFeatures `json:"experimentalFeatures"`
	ResLimitConfig       ResLimitConfig       `json:"resLimitConfig"`
}

// NewProjectConfig create project config
func NewProjectConfig() *ProjectConfig {
	conf := ProjectConfig{}
	// 预设默认值
	conf.ResLimitConfig.ProcDefaultCPULimits = "4"
	conf.ResLimitConfig.ProcDefaultMemLimits = "1Gi"
	conf.ResLimitConfig.MaxReplicas = 5

	return &conf
}

func init() {
	SchemeBuilder.Register(&ProjectConfig{})
}
