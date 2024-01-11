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
	// if MountLogsToHostPath is true, will mount /app/logs and /app/v3logs to host path
	MountLogsToHostPath bool `json:"mountLogsToHostPath,omitempty"`
}

// IngressPluginConfig contains the config for controlling ingress config
type IngressPluginConfig struct {
	AccessControl *AccessControlConfig `json:"accessControl,omitempty"`
	PaaSAnalysis  *PaaSAnalysisConfig  `json:"paasAnalysis,omitempty"`
}

// AccessControlConfig contains the config for controlling ingress snippet about Access control module
type AccessControlConfig struct {
	// bk-ingress-nginx choose which redis key to connect to, optional values 'prod', 'test', 'local'
	RedisConfigKey string `json:"redisConfigKey"`
}

// PaaSAnalysisConfig contains the config for controlling ingress snippet about PA(paas-analysis) module
type PaaSAnalysisConfig struct {
	// Is PA enabled on the current cluster?
	Enabled bool `json:"enabled"`
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

// AutoscalingConfig contains the config for autoscaling
type AutoscalingConfig struct {
	// Enabled indicates whether autoscaling is enabled
	Enabled bool `json:"enabled"`
}

//+kubebuilder:object:root=true

// ProjectConfig is the Schema for the project configs API
type ProjectConfig struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	// ControllerManagerConfigurationSpec returns the configurations for controllers
	cfg.ControllerManagerConfigurationSpec `json:",inline"`

	Platform      PlatformConfig      `json:"platform"`
	IngressPlugin IngressPluginConfig `json:"ingressPlugin"`
	ResLimit      ResLimitConfig      `json:"resLimit"`
	Autoscaling   AutoscalingConfig   `json:"autoscaling"`
	MaxProcesses  int32               `json:"maxProcesses"`
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
	conf.ResLimit.ProcDefaultCPULimits = "4000m"
	conf.ResLimit.ProcDefaultMemLimits = "1024Mi"
	conf.ResLimit.MaxReplicas = 5

	conf.MaxProcesses = 8

	return &conf
}

func init() {
	SchemeBuilder.Register(&ProjectConfig{})
}

// Below functions implements the ProjectConfigReader interface

// GetMaxProcesses returns the max processes
func (p *ProjectConfig) GetMaxProcesses() int32 {
	return p.MaxProcesses
}

// GetProcMaxReplicas returns the max replicas of a process
func (p *ProjectConfig) GetProcMaxReplicas() int32 {
	return p.ResLimit.MaxReplicas
}

// GetProcDefaultCpuLimits returns the default cpu limits of a process
func (p *ProjectConfig) GetProcDefaultCpuLimits() string {
	return p.ResLimit.ProcDefaultCPULimits
}

// GetProcDefaultMemLimits returns the default memory limits of a process
func (p *ProjectConfig) GetProcDefaultMemLimits() string {
	return p.ResLimit.ProcDefaultMemLimits
}

// GetIngressClassName returns the ingress class name
func (p *ProjectConfig) GetIngressClassName() string {
	return p.Platform.IngressClassName
}

// RequireMountLogsToHostPath returns whether mount logs to host path
func (p *ProjectConfig) RequireMountLogsToHostPath() bool {
	return p.Platform.MountLogsToHostPath
}

// IsAutoscalingEnabled returns whether autoscaling is enabled
func (p *ProjectConfig) IsAutoscalingEnabled() bool {
	return p.Autoscaling.Enabled
}
