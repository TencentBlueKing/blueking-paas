/*
Copyright 2022.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status

// DomainGroupMapping is the Schema for the domaingroupmappings API
type DomainGroupMapping struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   DomainGroupMappingSpec   `json:"spec,omitempty"`
	Status DomainGroupMappingStatus `json:"status,omitempty"`
}

// IsReferenceTo checks if the mapping object is reference to given BkApp object.
func (m DomainGroupMapping) IsReferenceTo(app BkApp) bool {
	return m.GetNamespace() == app.GetNamespace() && m.Spec.Ref.Kind == KindBkApp && m.Spec.Ref.Name == app.GetName()
}

// DomainGroupMappingSpec defines the desired state of DomainGroupMapping
type DomainGroupMappingSpec struct {
	Ref  MappingRef    `json:"ref"`
	Data []DomainGroup `json:"data"`
}

// MappingRef defines the referenced subject of current mapping object, usually BkApp.
type MappingRef struct {
	// Name of BkApp resource object, same namespace required
	Name       string `json:"name"`
	Kind       string `json:"kind"`
	APIVersion string `json:"apiVersion"`
}

// DomainGroup stores a group of domains
type DomainGroup struct {
	// SourceType shows by which source the Domains was provided
	SourceType string   `json:"sourceType"`
	Domains    []Domain `json:"domains"`
}

// Domain is a simple structure to store addressable locations
type Domain struct {
	// Name field is used to distinct Domain objects, it will appears in Ingress
	// resource name when source type is "custom", so only lower-cased letters
	// and numbers are allowed. It's user's responsibility to avoid collisions.
	//
	// +kubebuilder:validation:MaxLength:=32
	// +optional
	Name string `json:"name"`

	// Host is the domain name, e.g. "www.example.com"
	Host           string   `json:"host"`
	PathPrefixList []string `json:"pathPrefixList"`

	// TLSSecretName is the name of Secret resource which contains TLS certificates,
	// HTTPS is enabled when this field is provided.
	// +optional
	TLSSecretName string `json:"tlsSecretName"`
}

// DomainGroupMappingStatus defines the observed state of DomainGroupMapping
type DomainGroupMappingStatus struct {
	// Represents the latest available observations of a Mapping's current state.
	// +optional
	Conditions []metav1.Condition `json:"conditions"`
}

const (
	// DomainMappingProcessed means the Mapping object has been successfully
	// processed, referenced BkApp has observed current domain data.
	DomainMappingProcessed string = "DomainMappingProcessed"
)

//+kubebuilder:object:root=true

// DomainGroupMappingList contains a list of DomainGroupMapping
type DomainGroupMappingList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []DomainGroupMapping `json:"items"`
}

func init() {
	SchemeBuilder.Register(&DomainGroupMapping{}, &DomainGroupMappingList{})
}
