/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

package v1beta1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// SandboxInstance phase constants
const (
	SandboxPhasePending     = "Pending"
	SandboxPhaseCreating    = "Creating"
	SandboxPhaseRunning     = "Running"
	SandboxPhaseStopping    = "Stopping"
	SandboxPhaseStopped     = "Stopped"
	SandboxPhaseFailed      = "Failed"
	SandboxPhaseTerminating = "Terminating"
)

// SandboxInstance desired state constants
const (
	SandboxDesiredStateRunning = "Running"
	SandboxDesiredStateStopped = "Stopped"
)

// SandboxInstance is the Schema for the sandboxinstances API.
// CRD owned by sandbox-controller (advanced.bkbcs.tencent.com/v1beta1), not controlled by bkAppOperator.
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
type SandboxInstance struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              SandboxInstanceSpec   `json:"spec,omitempty"`
	Status            SandboxInstanceStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// SandboxInstanceList contains a list of SandboxInstance
type SandboxInstanceList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []SandboxInstance `json:"items"`
}

// SandboxInstanceSpec defines the desired state of a SandboxInstance
// +kubebuilder:object:generate=true
type SandboxInstanceSpec struct {
	// DesiredState is the desired running state: "Running" or "Stopped"
	DesiredState string `json:"desiredState"`

	// RuntimeClassName specifies the runtime class, typically "cube"
	RuntimeClassName string `json:"runtimeClassName"`

	// Network defines network configuration
	Network SandboxNetwork `json:"network"`

	// Domain is required by the SandboxInstance CRD.
	// 保留 domain 中的 cpu/memory 为空，由 sandbox controller 负责计算。
	Domain SandboxDomain `json:"domain"`

	// PodTemplate defines the pod template for the sandbox instance
	PodTemplate SandboxPodTemplate `json:"podTemplate"`

	// VolumeClaimTemplates are PVC templates for persistent storage
	// +optional
	VolumeClaimTemplates []corev1.PersistentVolumeClaim `json:"volumeClaimTemplates,omitempty"`
}

// SandboxNetwork defines network configuration for the sandbox
type SandboxNetwork struct {
	// Mode is the network mode, typically "direct-cni"
	Mode string `json:"mode"`
}

// SandboxDomain defines compute resource configuration
// +kubebuilder:object:generate=true
type SandboxDomain struct {
	// CPU configuration. Omit to let sandbox-controller derive from containers.
	// +optional
	CPU SandboxCPU `json:"cpu,omitempty"`

	// Memory quantity string, e.g. "4Gi". Omit to let sandbox-controller derive
	// from containers.
	// +optional
	Memory string `json:"memory,omitempty"`

	// Devices configuration (rootfs disks etc.)
	// +optional
	Devices *SandboxDevices `json:"devices,omitempty"`
}

// SandboxCPU defines CPU resource
type SandboxCPU struct {
	// Cores is the number of vCPU cores (integer)
	// +optional
	Cores int32 `json:"cores,omitempty"`
}

// SandboxDevices defines device configuration for rootfs etc.
// +kubebuilder:object:generate=true
type SandboxDevices struct {
	// Disks is a list of disk configurations
	// +optional
	Disks []SandboxDisk `json:"disks,omitempty"`
}

// SandboxDisk defines a disk configuration entry
type SandboxDisk struct {
	Name       string `json:"name"`
	VolumeName string `json:"volumeName"`
	Role       string `json:"role"`
	Image      string `json:"image"`
	SourcePath string `json:"sourcePath"`
	Size       string `json:"size"`
	FsType     string `json:"fsType"`
}

// SandboxPodTemplate defines the pod specification for the sandbox
// +kubebuilder:object:generate=true
type SandboxPodTemplate struct {
	// Containers is a list of containers in the sandbox pod.
	//
	// The patchStrategy/patchMergeKey tags mirror those on corev1.PodSpec. They are
	// only read by apimachinery's strategicpatch when computing a merge locally, and
	// have no effect on how the CR is serialized to the API server. Without them, a
	// strategic merge patch would replace the whole list instead of merging entries
	// by name, which would drop the main container when injecting sidecars.
	Containers []corev1.Container `json:"containers" patchStrategy:"merge" patchMergeKey:"name"`

	// Volumes to mount
	// +optional
	Volumes []corev1.Volume `json:"volumes,omitempty" patchStrategy:"merge,retainKeys" patchMergeKey:"name"`

	// NodeSelector for scheduling
	// +optional
	NodeSelector map[string]string `json:"nodeSelector,omitempty"`

	// Tolerations for scheduling
	// +optional
	Tolerations []corev1.Toleration `json:"tolerations,omitempty"`

	// DNSConfig for custom DNS settings
	// +optional
	DNSConfig *corev1.PodDNSConfig `json:"dnsConfig,omitempty"`

	// HostAliases for /etc/hosts entries
	// +optional
	HostAliases []corev1.HostAlias `json:"hostAliases,omitempty"`

	// ImagePullSecrets for pulling private images
	// +optional
	ImagePullSecrets []corev1.LocalObjectReference `json:"imagePullSecrets,omitempty"`

	// Labels to add to the pod (sandbox-controller inherits these from CR metadata)
	// +optional
	Labels map[string]string `json:"labels,omitempty"`
}

// SandboxInstanceStatus defines the observed state of SandboxInstance
type SandboxInstanceStatus struct {
	// Phase is the current lifecycle phase: Pending, Creating, Running, Stopping, Stopped, Failed, Terminating
	// +optional
	Phase string `json:"phase,omitempty"`

	// Message provides additional information about the current phase
	// +optional
	Message string `json:"message,omitempty"`

	// ObservedGeneration reflects the generation most recently observed by sandbox-controller
	// +optional
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// SandboxIP is the IP address of the running sandbox
	// +optional
	SandboxIP string `json:"sandboxIP,omitempty"`

	// PodName is the name of the rendered cube Pod
	// +optional
	PodName string `json:"podName,omitempty"`

	// NodeName is the node where the sandbox pod is scheduled
	// +optional
	NodeName string `json:"nodeName,omitempty"`
}

func init() {
	SchemeBuilder.Register(&SandboxInstance{}, &SandboxInstanceList{})
}
