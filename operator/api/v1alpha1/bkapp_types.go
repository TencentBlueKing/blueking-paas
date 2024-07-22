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
	"encoding/json"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// BkApp is the Schema for the bkapps API
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="PreRelease Hook Phase",type=string,JSONPath=`.status.hookStatuses[?(@.type == "pre-release")].phase`
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"
type BkApp struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              AppSpec   `json:"spec,omitempty"`
	Status            AppStatus `json:"status,omitempty"`
}

// ExtractAddons will return the addon name list defined in the annotations, if not found, return nil and err
func (bkapp *BkApp) ExtractAddons() ([]string, error) {
	// 未声明增强服务, 返回空列表
	val, ok := bkapp.Annotations[AddonsAnnoKey]
	if !ok {
		return nil, nil
	}

	var addons []string
	if err := json.Unmarshal([]byte(val), &addons); err != nil {
		return nil, errors.WithStack(err)
	}
	return addons, nil
}

//+kubebuilder:object:root=true

// BkAppList contains a list of BkApp
type BkAppList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []BkApp `json:"items"`
}

// AppSpec defines the desired state of BkApp
type AppSpec struct {
	// +optional
	Build         BuildConfig `json:"build"`
	Processes     []Process   `json:"processes"`
	Configuration AppConfig   `json:"configuration"`

	// Addons is a list of add-on service
	// +optional
	Addons []paasv1alpha2.Addon `json:"addons,omitempty"`

	// Hook commands of current BkApp resource
	// +optional
	Hooks *AppHooks `json:"hooks,omitempty"`

	// EnvOverlay holds environment specified configurations, includes replica
	// count and environment variables.
	// +optional
	EnvOverlay *AppEnvOverlay `json:"envOverlay,omitempty"`
}

// GetWebProcess will find the web process in Spec.Processes
func (spec *AppSpec) GetWebProcess() *Process {
	return spec.FindProcess(WebProcName)
}

// FindProcess will find the process with given name
func (spec *AppSpec) FindProcess(name string) *Process {
	for _, proc := range spec.Processes {
		if proc.Name == name {
			return &proc
		}
	}
	return nil
}

// BuildConfig is the configuration related with application building, the platform
// support 3 types of build config currently: image, remote build by Dockerfile and
// remote build by buildpack.
type BuildConfig struct {
	// *1. Build by image*
	// Image is the container image name of current application, tag and container
	// registry address can be included.
	// +optional
	Image string `json:"image,omitempty"`
	// ImagePullPolicy is the image pull policy of given image.
	// +optional
	ImagePullPolicy corev1.PullPolicy `json:"imagePullPolicy,omitempty"`
	// ImageCredentialsName is the name of image credentials, required for pulling
	// images stores in private registry.
	// +optional
	ImageCredentialsName string `json:"imageCredentialsName,omitempty"`

	// *2. Remote build by Dockerfile*
	// Dockerfile is the name of target Dockerfile, it will be used to build.
	// +optional
	Dockerfile string `json:"dockerfile,omitempty"`
	// BuildTarget, when multiple stages are defined in Dockerfile, this field is used
	// to specify the target stage.
	// +optional
	BuildTarget string `json:"buildTarget,omitempty"`
	// Args is the additional build arguments, it will be used to build image by Dockerfile
	// +optional
	Args map[string]string `json:"args,omitempty"`

	// *3. Remote build by buildpack*
	// TODO
}

// Process defines the process of BkApp
type Process struct {
	// Name of process
	Name string `json:"name"`

	// Container image name
	Image string `json:"image"`

	// Container image pull policy
	ImagePullPolicy corev1.PullPolicy `json:"imagePullPolicy,omitempty"`

	// Replicas will be used as deployment's spec.replicas
	Replicas *int32 `json:"replicas"`

	// Services is a list of ProcService which used to expose process network for access within or outside the cluster.
	// +optional
	Services []paasv1alpha2.ProcService `json:"services,omitempty"`

	// ResQuotaPlan is the name of plan which defines how much resources current process
	// can consume.
	ResQuotaPlan paasv1alpha2.ResQuotaPlan `json:"resQuotaPlan,omitempty"`

	// The containerPort to expose server
	TargetPort int32 `json:"targetPort,omitempty"`

	// CPU will be used as limits.cpu
	CPU string `json:"cpu,omitempty"`

	// Memory will be used as limits.memory
	Memory string `json:"memory,omitempty"`

	// Entrypoint array. Not executed within a shell.
	Command []string `json:"command,omitempty"`

	// Arguments to the entrypoint.
	Args []string `json:"args,omitempty"`

	// Autoscaling specifies the autoscaling configuration
	Autoscaling *AutoscalingSpec `json:"autoscaling,omitempty"`

	// Probes specifies the probe configuration
	Probes *ProbeSet `json:"probes,omitempty"`
}

// AutoscalingSpec is bkapp autoscaling config
type AutoscalingSpec struct {
	// minReplicas is the lower limit for the number of replicas to which the autoscaler can scale down.
	// It defaults to 1 pod. minReplicas is allowed to be 0 if the alpha feature gate GPAScaleToZero
	// is enabled and at least one Object or External metric is configured. Scaling is active as long as
	// at least one metric value is available
	MinReplicas int32 `json:"minReplicas"`

	// maxReplicas is the upper limit for the number of replicas to which the autoscaler can scale up.
	// It cannot be less that minReplicas.
	MaxReplicas int32 `json:"maxReplicas"`

	// Policy defines the policy for autoscaling, its optional values depend on the policies supported by the operator.
	Policy ScalingPolicy `json:"policy"`
}

// ScalingPolicy is used to specify which policy should be used while scaling
type ScalingPolicy string

const (
	// ScalingPolicyDefault is the default autoscaling policy (cpu utilization 85%)
	ScalingPolicyDefault ScalingPolicy = "default"
)

// ProbeSet defines the probes configuration
type ProbeSet struct {
	// liveness is the configuration for liveness probes.
	// +optional
	Liveness *corev1.Probe `json:"liveness,omitempty"`
	// ReadinessProbe is the configuration for readiness probes.
	// +optional
	Readiness *corev1.Probe `json:"readiness,omitempty"`
	// StartupProbe is the configuration for startup probes.
	// +optional
	Startup *corev1.Probe `json:"startup,omitempty"`
}

// AppHooks defines bkapp deployment hook
type AppHooks struct {
	PreRelease *Hook `json:"preRelease,omitempty"`
}

// Hook is a set of commands to execute during bkapp deployment, running, and termination
type Hook struct {
	// Entrypoint array. Not executed within a shell.
	Command []string `json:"command,omitempty"`

	// Arguments to the entrypoint.
	Args []string `json:"args,omitempty"`
}

// AppConfig is bkapp related configuration, such as environment variables, etc.
type AppConfig struct {
	// List of environment variables to set in the container.
	Env []AppEnvVar `json:"env,omitempty"`
}

// AppEnvVar defines the environment variable of bkapp
type AppEnvVar struct {
	// Name of the environment variable. Must be a C_IDENTIFIER.
	Name string `json:"name"`

	// Value of the environment variable
	Value string `json:"value"`
}

// AppEnvOverlay defines environment specified configs.
type AppEnvOverlay struct {
	// Replicas overwrite process's replicas count
	// +optional
	Replicas []ReplicasOverlay `json:"replicas,omitempty"`

	// ResQuotas overwrite BkApp's process resource quota
	// +optional
	ResQuotas []ResQuotaOverlay `json:"resQuotas,omitempty"`

	// EnvVariables overwrite BkApp's environment vars
	// +optional
	EnvVariables []EnvVarOverlay `json:"envVariables,omitempty"`

	// Autoscaling overwrite process's autoscaling config
	// +optional
	Autoscaling []AutoscalingOverlay `json:"autoscaling,omitempty"`
}

// EnvName is the environment name for application deployment
type EnvName string

// IsEmpty checks if current environment is empty(absent)
func (n EnvName) IsEmpty() bool {
	return string(n) == ""
}

// IsValid checks if a given string is valid as environment name
func (n EnvName) IsValid() bool {
	return n == StagEnv || n == ProdEnv
}

const (
	// StagEnv refers to "stage" env
	StagEnv EnvName = "stag"
	// ProdEnv refers to "production" env
	ProdEnv EnvName = "prod"
)

// ReplicasOverlay overwrite process's replicas by environment.
type ReplicasOverlay struct {
	// EnvName is app environment name
	EnvName EnvName `json:"envName"`
	// Process is the name of process
	Process string `json:"process"`
	// Count is the desired replicas for current process
	Count int32 `json:"count"`
}

// ResQuotaOverlay overwrite process's resQuota by environment.
type ResQuotaOverlay struct {
	// EnvName is app environment name
	EnvName EnvName `json:"envName"`
	// Process is the name of process
	Process string `json:"process"`
	// Plan is used to specify process resource quota
	Plan paasv1alpha2.ResQuotaPlan `json:"plan"`
}

// EnvVarOverlay overwrite or add application's environment vars by environment.
type EnvVarOverlay struct {
	// EnvName is app environment name
	EnvName EnvName `json:"envName"`
	// Name of the environment variable. Must be a C_IDENTIFIER.
	Name string `json:"name"`
	// Value of the environment variable
	Value string `json:"value"`
}

// AutoscalingOverlay overwrite or add application's autoscaling config by environment.
type AutoscalingOverlay struct {
	// EnvName is app environment name
	EnvName EnvName `json:"envName"`
	// Process is the name of process
	Process string `json:"process"`
	// Spec is bkapp autoscaling config
	AutoscalingSpec `json:",inline"`
}

// AppStatus defines the observed state of BkApp
type AppStatus struct {
	// The phase of a BkApp is a simple, high-level summary of where the BkApp is in its lifecycle.
	Phase AppPhase `json:"phase"`

	// Conditions Represents the latest available observations of a BkApp's current state.
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// Addresses holds all addressable locations of current BkApp, user may visit
	// app via these locations, includes all domain source types.
	// +optional
	Addresses []Addressable `json:"addresses,omitempty"`

	// HookStatuses is the status of Hook execution
	HookStatuses []HookStatus `json:"hookStatuses,omitempty"`

	// Revision of the BkApp configuration it generates
	Revision *Revision `json:"revision,omitempty"`

	// DeployId of the BkApp, which is injected from bkpaas
	DeployId string `json:"deployId,omitempty"`

	// LastUpdate is the bkapp's last update time
	LastUpdate *metav1.Time `json:"lastUpdate,omitempty"`

	// observedGeneration is the most recent generation observed for this BkApp. It corresponds to the
	// .metadata.generation, which is updated on mutation by the API Server.
	// +optional
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// AddonStatuses is the status of add-on service include specifications
	// +optional
	AddonStatuses []paasv1alpha2.AddonStatus `json:"addonStatuses,omitempty"`
}

// Addressable includes URL and other related properties
type Addressable struct {
	// SourceType, see CRD DomainGroupMapping for more details
	SourceType string `json:"sourceType"`

	// URL generally has the form "http[s]://{hostname}/{subpath}/"
	URL string `json:"url"`
}

// AppPhase is a label for the condition of a BkApp at the current time.
// +enum
type AppPhase string

const (
	// AppPending means the BkApp has been accepted by the system, but one or more of the reconcile steps
	// has not been finished.
	AppPending AppPhase = "Pending"
	// AppRunning means the BkApp has been bound to a cluster and all Process have been started.
	AppRunning AppPhase = "Running"
	// AppFailed means that  at least one Process in the BkApp have terminated in a failure (exited with
	// a non-zero exit code or was stopped by the system). Or some necessary reconcile steps failed.
	AppFailed AppPhase = "Failed"
)

const (
	// AppAvailable means the BkApp is available and ready to service requests, all
	// processes should be up and running for at least "minReadySeconds".
	AppAvailable string = "AppAvailable"

	// AppProgressing means the BkApp is progressing. Progress for a BkApp is considered
	// when new processes are created or old processes scale down.
	AppProgressing string = "AppProgressing"

	// AddOnsProvisioned means all types of Add-on are successfully provisioned
	AddOnsProvisioned string = "AddOnsProvisioned"

	// HooksFinished means all hook commands have been finished for CURRENT REVISION,
	// when new revisions are deployed, the condition will be reset.
	HooksFinished string = "HooksFinished"
)

// HookType hook type
type HookType string

const (
	// HookPreRelease is a hook will run after bkapp crd create and before bkapp's process create
	HookPreRelease HookType = "pre-release"
)

// SetDeployID set the DeployID field in the status.
func (status *AppStatus) SetDeployID(deployId string) {
	status.DeployId = deployId
	status.LastUpdate = lo.ToPtr(metav1.Now())
}

// SetHookStatus used to set the HookStatuses field (and update the LastUpdate field)
func (status *AppStatus) SetHookStatus(hookStatus HookStatus) {
	status.LastUpdate = lo.ToPtr(metav1.Now())

	existingStatus := status.FindHookStatus(hookStatus.Type)
	if existingStatus == nil {
		hookStatus.setLastTransitionTime(hookStatus.LastTransitionTime)
		status.HookStatuses = append(status.HookStatuses, hookStatus)
		return
	}

	if existingStatus.Phase != hookStatus.Phase {
		existingStatus.Phase = hookStatus.Phase
		existingStatus.setLastTransitionTime(hookStatus.LastTransitionTime)
	}

	// avoid overwrite by zero values, to protect those logical that depend on this value
	if hookStatus.Started != nil {
		existingStatus.Started = hookStatus.Started
	}
	if !hookStatus.StartTime.IsZero() {
		existingStatus.StartTime = hookStatus.StartTime
	}
	existingStatus.Reason = hookStatus.Reason
	existingStatus.Message = hookStatus.Message
}

// FindHookStatus used to find the given hook status with
func (status *AppStatus) FindHookStatus(hookType HookType) *HookStatus {
	if len(status.HookStatuses) == 0 {
		return nil
	}

	for i := range status.HookStatuses {
		if status.HookStatuses[i].Type == hookType {
			return &status.HookStatuses[i]
		}
	}
	return nil
}

// HealthPhase Represents resource health status, such as pod, deployment(man by in the feature)
// For a Pod, healthy is meaning that the Pod is successfully complete or is Ready
//
//	unhealthy is meaning that the Pod is restarting or is Failed
//	progressing is meaning that the Pod is still running and condition `PodReady` is False.
type HealthPhase string

const (
	// HealthHealthy  resource is healthy
	HealthHealthy HealthPhase = "Healthy"
	// HealthUnhealthy resource is unhealthy
	HealthUnhealthy HealthPhase = "Unhealthy"
	// HealthProgressing resource is still progressing
	HealthProgressing HealthPhase = "Progressing"
	// HealthUnknown health status is unknown
	HealthUnknown HealthPhase = "Unknown"
)

// HookStatus define the status of Hook execution
type HookStatus struct {
	Type HookType `json:"type"`

	// Started is true when hook is started
	Started *bool `json:"started,omitempty"`
	// The hook's start time
	StartTime *metav1.Time `json:"startTime,omitempty"`

	// Phase Represents the hook pod health status
	Phase HealthPhase `json:"phase"`
	// if pod is unhealthy, message will be the fail message, otherwise, same with PodStatus.Message
	Message string `json:"message,omitempty"`
	// Same with PodStatus.Reason
	Reason string `json:"reason,omitempty"`
	// lastTransitionTime is the last time the status transitioned from one status to another.
	// +optional
	LastTransitionTime *metav1.Time `json:"lastTransitionTime,omitempty"`
}

// setLastTransitionTime will set the LastTransitionTime Field by given time or Now(when given time is zero)
func (status *HookStatus) setLastTransitionTime(time *metav1.Time) {
	if !time.IsZero() {
		status.LastTransitionTime = time
	} else {
		status.LastTransitionTime = lo.ToPtr(metav1.Now())
	}
}

// Revision define the version info
type Revision struct {
	// BkApp's version
	Revision int64 `json:"revision"`
}

func init() {
	SchemeBuilder.Register(&BkApp{}, &BkAppList{})
}
