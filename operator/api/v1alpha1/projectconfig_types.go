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
	// sentry server dsn, all events waiting for report will be dropped if unset
	SentryDSN string `json:"sentryDSN"`
	// if ingressClassName configured, kubernetes.io/ingress.class=$value will be added to ingress's annotations
	IngressClassName string `json:"ingressClassName"`
	// CustomDomainIngressClassName works the same as IngressClassName, but only for ingress with custom domains.
	// Set customDomainIngressClassName if custom domain ingress needs to bound to a specific ingress controller,
	// otherwise it will be bound to the ingress controller specified by ingressClassName config
	CustomDomainIngressClassName string `json:"customDomainIngressClassName"`
}

// IngressPluginConfig contains the config for controlling ingress config
type IngressPluginConfig struct {
	AccessControl *AccessControlConfig `json:"accessControl,omitempty"`
	PaaSAnalysis  *PaaSAnalysisConfig  `json:"paasAnalysis,omitempty"`
	TenantGuard   *TenantGuardConfig   `json:"tenantGuard,omitempty"`
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

// TenantGuardConfig contains the config for controlling ingress snippet about TenantGuard.
// If TenantGuard is enabled, tenantGuardTemplate will be rendered in ingress.
type TenantGuardConfig struct {
	// Enabled true if TenantGuard is enabled
	Enabled bool `json:"enabled"`
}

// ResLimitsConfig contains bkapp resource limits
type ResLimitsConfig struct {
	// ProcDefaultCPULimit is process's default cpu quota
	ProcDefaultCPULimit string `json:"procDefaultCPULimit"`

	// ProcDefaultMemLimit is process's default memory quota
	ProcDefaultMemLimit string `json:"procDefaultMemLimit"`

	// MaxReplicas is single instance max replica num
	MaxReplicas int32 `json:"maxReplicas"`
}

// ResRequestsConfig contains bkapp resource requests
type ResRequestsConfig struct {
	// ProcDefaultCPURequest is process's default cpu request
	ProcDefaultCPURequest string `json:"procDefaultCPURequest"`

	// ProcDefaultMemRequest is process's default memory request
	ProcDefaultMemRequest string `json:"procDefaultMemRequest"`
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
	ResLimits     ResLimitsConfig     `json:"resLimits"`
	// NOTE: ResRequests 是 operator 为 BkApp 设置的默认 resource requests,
	// 仅当 BkApp 中 ResourceQuota 没有提供 requests 的情况下有效
	ResRequests  ResRequestsConfig `json:"resRequests"`
	Autoscaling  AutoscalingConfig `json:"autoscaling"`
	MaxProcesses int32             `json:"maxProcesses"`
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
	conf.ResLimits.ProcDefaultCPULimit = "4000m"
	conf.ResLimits.ProcDefaultMemLimit = "1024Mi"
	conf.ResLimits.MaxReplicas = 5

	// 资源请求默认值
	conf.ResRequests.ProcDefaultMemRequest = ""
	conf.ResRequests.ProcDefaultCPURequest = ""

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
	return p.ResLimits.MaxReplicas
}

// GetProcDefaultCpuLimit returns the default cpu limit of a process
func (p *ProjectConfig) GetProcDefaultCpuLimit() string {
	return p.ResLimits.ProcDefaultCPULimit
}

// GetProcDefaultMemLimit returns the default memory limit of a process
func (p *ProjectConfig) GetProcDefaultMemLimit() string {
	return p.ResLimits.ProcDefaultMemLimit
}

// GetProcDefaultCpuRequest returns the default cpu request of a process
func (p *ProjectConfig) GetProcDefaultCpuRequest() string {
	return p.ResRequests.ProcDefaultCPURequest
}

// GetProcDefaultMemRequest returns the default cpu limit of a process
func (p *ProjectConfig) GetProcDefaultMemRequest() string {
	return p.ResRequests.ProcDefaultMemRequest
}

// GetIngressClassName returns the ingress class name
func (p *ProjectConfig) GetIngressClassName() string {
	return p.Platform.IngressClassName
}

// GetCustomDomainIngressClassName returns the ingress class name for custom domain ingress.
// if not set, return the common ingress class name
func (p *ProjectConfig) GetCustomDomainIngressClassName() string {
	if p.Platform.CustomDomainIngressClassName != "" {
		return p.Platform.CustomDomainIngressClassName
	}
	return p.GetIngressClassName()
}

// IsAutoscalingEnabled returns whether autoscaling is enabled
func (p *ProjectConfig) IsAutoscalingEnabled() bool {
	return p.Autoscaling.Enabled
}
