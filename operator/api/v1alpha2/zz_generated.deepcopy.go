//go:build !ignore_autogenerated

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

// Code generated by controller-gen. DO NOT EDIT.

package v1alpha2

import (
	"k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Addon) DeepCopyInto(out *Addon) {
	*out = *in
	if in.Specs != nil {
		in, out := &in.Specs, &out.Specs
		*out = make([]AddonSpec, len(*in))
		copy(*out, *in)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Addon.
func (in *Addon) DeepCopy() *Addon {
	if in == nil {
		return nil
	}
	out := new(Addon)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AddonSpec) DeepCopyInto(out *AddonSpec) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AddonSpec.
func (in *AddonSpec) DeepCopy() *AddonSpec {
	if in == nil {
		return nil
	}
	out := new(AddonSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AddonStatus) DeepCopyInto(out *AddonStatus) {
	*out = *in
	if in.Specs != nil {
		in, out := &in.Specs, &out.Specs
		*out = make([]AddonSpec, len(*in))
		copy(*out, *in)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AddonStatus.
func (in *AddonStatus) DeepCopy() *AddonStatus {
	if in == nil {
		return nil
	}
	out := new(AddonStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Addressable) DeepCopyInto(out *Addressable) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Addressable.
func (in *Addressable) DeepCopy() *Addressable {
	if in == nil {
		return nil
	}
	out := new(Addressable)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppConfig) DeepCopyInto(out *AppConfig) {
	*out = *in
	if in.Env != nil {
		in, out := &in.Env, &out.Env
		*out = make([]AppEnvVar, len(*in))
		copy(*out, *in)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppConfig.
func (in *AppConfig) DeepCopy() *AppConfig {
	if in == nil {
		return nil
	}
	out := new(AppConfig)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppEnvOverlay) DeepCopyInto(out *AppEnvOverlay) {
	*out = *in
	if in.Replicas != nil {
		in, out := &in.Replicas, &out.Replicas
		*out = make([]ReplicasOverlay, len(*in))
		copy(*out, *in)
	}
	if in.ResQuotas != nil {
		in, out := &in.ResQuotas, &out.ResQuotas
		*out = make([]ResQuotaOverlay, len(*in))
		copy(*out, *in)
	}
	if in.EnvVariables != nil {
		in, out := &in.EnvVariables, &out.EnvVariables
		*out = make([]EnvVarOverlay, len(*in))
		copy(*out, *in)
	}
	if in.Autoscaling != nil {
		in, out := &in.Autoscaling, &out.Autoscaling
		*out = make([]AutoscalingOverlay, len(*in))
		copy(*out, *in)
	}
	if in.Mounts != nil {
		in, out := &in.Mounts, &out.Mounts
		*out = make([]MountOverlay, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppEnvOverlay.
func (in *AppEnvOverlay) DeepCopy() *AppEnvOverlay {
	if in == nil {
		return nil
	}
	out := new(AppEnvOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppEnvVar) DeepCopyInto(out *AppEnvVar) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppEnvVar.
func (in *AppEnvVar) DeepCopy() *AppEnvVar {
	if in == nil {
		return nil
	}
	out := new(AppEnvVar)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppHooks) DeepCopyInto(out *AppHooks) {
	*out = *in
	if in.PreRelease != nil {
		in, out := &in.PreRelease, &out.PreRelease
		*out = new(Hook)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppHooks.
func (in *AppHooks) DeepCopy() *AppHooks {
	if in == nil {
		return nil
	}
	out := new(AppHooks)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppSpec) DeepCopyInto(out *AppSpec) {
	*out = *in
	in.Build.DeepCopyInto(&out.Build)
	if in.Processes != nil {
		in, out := &in.Processes, &out.Processes
		*out = make([]Process, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	in.Configuration.DeepCopyInto(&out.Configuration)
	if in.Addons != nil {
		in, out := &in.Addons, &out.Addons
		*out = make([]Addon, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	if in.Mounts != nil {
		in, out := &in.Mounts, &out.Mounts
		*out = make([]Mount, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	if in.Hooks != nil {
		in, out := &in.Hooks, &out.Hooks
		*out = new(AppHooks)
		(*in).DeepCopyInto(*out)
	}
	if in.DomainResolution != nil {
		in, out := &in.DomainResolution, &out.DomainResolution
		*out = new(DomainResConfig)
		(*in).DeepCopyInto(*out)
	}
	if in.SvcDiscovery != nil {
		in, out := &in.SvcDiscovery, &out.SvcDiscovery
		*out = new(SvcDiscConfig)
		(*in).DeepCopyInto(*out)
	}
	if in.EnvOverlay != nil {
		in, out := &in.EnvOverlay, &out.EnvOverlay
		*out = new(AppEnvOverlay)
		(*in).DeepCopyInto(*out)
	}
	if in.Observability != nil {
		in, out := &in.Observability, &out.Observability
		*out = new(Observability)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppSpec.
func (in *AppSpec) DeepCopy() *AppSpec {
	if in == nil {
		return nil
	}
	out := new(AppSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AppStatus) DeepCopyInto(out *AppStatus) {
	*out = *in
	if in.Conditions != nil {
		in, out := &in.Conditions, &out.Conditions
		*out = make([]metav1.Condition, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	if in.Addresses != nil {
		in, out := &in.Addresses, &out.Addresses
		*out = make([]Addressable, len(*in))
		copy(*out, *in)
	}
	if in.HookStatuses != nil {
		in, out := &in.HookStatuses, &out.HookStatuses
		*out = make([]HookStatus, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	if in.Revision != nil {
		in, out := &in.Revision, &out.Revision
		*out = new(Revision)
		**out = **in
	}
	if in.LastUpdate != nil {
		in, out := &in.LastUpdate, &out.LastUpdate
		*out = (*in).DeepCopy()
	}
	if in.AddonStatuses != nil {
		in, out := &in.AddonStatuses, &out.AddonStatuses
		*out = make([]AddonStatus, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AppStatus.
func (in *AppStatus) DeepCopy() *AppStatus {
	if in == nil {
		return nil
	}
	out := new(AppStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AutoscalingOverlay) DeepCopyInto(out *AutoscalingOverlay) {
	*out = *in
	out.AutoscalingSpec = in.AutoscalingSpec
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AutoscalingOverlay.
func (in *AutoscalingOverlay) DeepCopy() *AutoscalingOverlay {
	if in == nil {
		return nil
	}
	out := new(AutoscalingOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *AutoscalingSpec) DeepCopyInto(out *AutoscalingSpec) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new AutoscalingSpec.
func (in *AutoscalingSpec) DeepCopy() *AutoscalingSpec {
	if in == nil {
		return nil
	}
	out := new(AutoscalingSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *BkApp) DeepCopyInto(out *BkApp) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	in.Status.DeepCopyInto(&out.Status)
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new BkApp.
func (in *BkApp) DeepCopy() *BkApp {
	if in == nil {
		return nil
	}
	out := new(BkApp)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *BkApp) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *BkAppList) DeepCopyInto(out *BkAppList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		in, out := &in.Items, &out.Items
		*out = make([]BkApp, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new BkAppList.
func (in *BkAppList) DeepCopy() *BkAppList {
	if in == nil {
		return nil
	}
	out := new(BkAppList)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *BkAppList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *BuildConfig) DeepCopyInto(out *BuildConfig) {
	*out = *in
	if in.Args != nil {
		in, out := &in.Args, &out.Args
		*out = make(map[string]string, len(*in))
		for key, val := range *in {
			(*out)[key] = val
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new BuildConfig.
func (in *BuildConfig) DeepCopy() *BuildConfig {
	if in == nil {
		return nil
	}
	out := new(BuildConfig)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ConfigMapSource) DeepCopyInto(out *ConfigMapSource) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ConfigMapSource.
func (in *ConfigMapSource) DeepCopy() *ConfigMapSource {
	if in == nil {
		return nil
	}
	out := new(ConfigMapSource)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *DomainResConfig) DeepCopyInto(out *DomainResConfig) {
	*out = *in
	if in.Nameservers != nil {
		in, out := &in.Nameservers, &out.Nameservers
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.HostAliases != nil {
		in, out := &in.HostAliases, &out.HostAliases
		*out = make([]HostAlias, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new DomainResConfig.
func (in *DomainResConfig) DeepCopy() *DomainResConfig {
	if in == nil {
		return nil
	}
	out := new(DomainResConfig)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *EnvVarOverlay) DeepCopyInto(out *EnvVarOverlay) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new EnvVarOverlay.
func (in *EnvVarOverlay) DeepCopy() *EnvVarOverlay {
	if in == nil {
		return nil
	}
	out := new(EnvVarOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ExposedType) DeepCopyInto(out *ExposedType) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ExposedType.
func (in *ExposedType) DeepCopy() *ExposedType {
	if in == nil {
		return nil
	}
	out := new(ExposedType)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Hook) DeepCopyInto(out *Hook) {
	*out = *in
	if in.Command != nil {
		in, out := &in.Command, &out.Command
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.Args != nil {
		in, out := &in.Args, &out.Args
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Hook.
func (in *Hook) DeepCopy() *Hook {
	if in == nil {
		return nil
	}
	out := new(Hook)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *HookStatus) DeepCopyInto(out *HookStatus) {
	*out = *in
	if in.Started != nil {
		in, out := &in.Started, &out.Started
		*out = new(bool)
		**out = **in
	}
	if in.StartTime != nil {
		in, out := &in.StartTime, &out.StartTime
		*out = (*in).DeepCopy()
	}
	if in.LastTransitionTime != nil {
		in, out := &in.LastTransitionTime, &out.LastTransitionTime
		*out = (*in).DeepCopy()
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new HookStatus.
func (in *HookStatus) DeepCopy() *HookStatus {
	if in == nil {
		return nil
	}
	out := new(HookStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *HostAlias) DeepCopyInto(out *HostAlias) {
	*out = *in
	if in.Hostnames != nil {
		in, out := &in.Hostnames, &out.Hostnames
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new HostAlias.
func (in *HostAlias) DeepCopy() *HostAlias {
	if in == nil {
		return nil
	}
	out := new(HostAlias)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in LegacyProcConfig) DeepCopyInto(out *LegacyProcConfig) {
	{
		in := &in
		*out = make(LegacyProcConfig, len(*in))
		for key, val := range *in {
			var outVal map[string]string
			if val == nil {
				(*out)[key] = nil
			} else {
				inVal := (*in)[key]
				in, out := &inVal, &outVal
				*out = make(map[string]string, len(*in))
				for key, val := range *in {
					(*out)[key] = val
				}
			}
			(*out)[key] = outVal
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LegacyProcConfig.
func (in LegacyProcConfig) DeepCopy() LegacyProcConfig {
	if in == nil {
		return nil
	}
	out := new(LegacyProcConfig)
	in.DeepCopyInto(out)
	return *out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Metric) DeepCopyInto(out *Metric) {
	*out = *in
	if in.Params != nil {
		in, out := &in.Params, &out.Params
		*out = make(map[string]string, len(*in))
		for key, val := range *in {
			(*out)[key] = val
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Metric.
func (in *Metric) DeepCopy() *Metric {
	if in == nil {
		return nil
	}
	out := new(Metric)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Monitoring) DeepCopyInto(out *Monitoring) {
	*out = *in
	if in.Metrics != nil {
		in, out := &in.Metrics, &out.Metrics
		*out = make([]Metric, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Monitoring.
func (in *Monitoring) DeepCopy() *Monitoring {
	if in == nil {
		return nil
	}
	out := new(Monitoring)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Mount) DeepCopyInto(out *Mount) {
	*out = *in
	if in.Source != nil {
		in, out := &in.Source, &out.Source
		*out = new(VolumeSource)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Mount.
func (in *Mount) DeepCopy() *Mount {
	if in == nil {
		return nil
	}
	out := new(Mount)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *MountOverlay) DeepCopyInto(out *MountOverlay) {
	*out = *in
	in.Mount.DeepCopyInto(&out.Mount)
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new MountOverlay.
func (in *MountOverlay) DeepCopy() *MountOverlay {
	if in == nil {
		return nil
	}
	out := new(MountOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Observability) DeepCopyInto(out *Observability) {
	*out = *in
	in.Monitoring.DeepCopyInto(&out.Monitoring)
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Observability.
func (in *Observability) DeepCopy() *Observability {
	if in == nil {
		return nil
	}
	out := new(Observability)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *PersistentStorage) DeepCopyInto(out *PersistentStorage) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new PersistentStorage.
func (in *PersistentStorage) DeepCopy() *PersistentStorage {
	if in == nil {
		return nil
	}
	out := new(PersistentStorage)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ProbeSet) DeepCopyInto(out *ProbeSet) {
	*out = *in
	if in.Liveness != nil {
		in, out := &in.Liveness, &out.Liveness
		*out = new(v1.Probe)
		(*in).DeepCopyInto(*out)
	}
	if in.Readiness != nil {
		in, out := &in.Readiness, &out.Readiness
		*out = new(v1.Probe)
		(*in).DeepCopyInto(*out)
	}
	if in.Startup != nil {
		in, out := &in.Startup, &out.Startup
		*out = new(v1.Probe)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ProbeSet.
func (in *ProbeSet) DeepCopy() *ProbeSet {
	if in == nil {
		return nil
	}
	out := new(ProbeSet)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ProcImageGetter) DeepCopyInto(out *ProcImageGetter) {
	*out = *in
	if in.bkapp != nil {
		in, out := &in.bkapp, &out.bkapp
		*out = new(BkApp)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ProcImageGetter.
func (in *ProcImageGetter) DeepCopy() *ProcImageGetter {
	if in == nil {
		return nil
	}
	out := new(ProcImageGetter)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ProcService) DeepCopyInto(out *ProcService) {
	*out = *in
	if in.ExposedType != nil {
		in, out := &in.ExposedType, &out.ExposedType
		*out = new(ExposedType)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ProcService.
func (in *ProcService) DeepCopy() *ProcService {
	if in == nil {
		return nil
	}
	out := new(ProcService)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Process) DeepCopyInto(out *Process) {
	*out = *in
	if in.Replicas != nil {
		in, out := &in.Replicas, &out.Replicas
		*out = new(int32)
		**out = **in
	}
	if in.Services != nil {
		in, out := &in.Services, &out.Services
		*out = make([]ProcService, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
	if in.Command != nil {
		in, out := &in.Command, &out.Command
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.Args != nil {
		in, out := &in.Args, &out.Args
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.Autoscaling != nil {
		in, out := &in.Autoscaling, &out.Autoscaling
		*out = new(AutoscalingSpec)
		**out = **in
	}
	if in.Probes != nil {
		in, out := &in.Probes, &out.Probes
		*out = new(ProbeSet)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Process.
func (in *Process) DeepCopy() *Process {
	if in == nil {
		return nil
	}
	out := new(Process)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ReplicasOverlay) DeepCopyInto(out *ReplicasOverlay) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ReplicasOverlay.
func (in *ReplicasOverlay) DeepCopy() *ReplicasOverlay {
	if in == nil {
		return nil
	}
	out := new(ReplicasOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ResQuotaOverlay) DeepCopyInto(out *ResQuotaOverlay) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ResQuotaOverlay.
func (in *ResQuotaOverlay) DeepCopy() *ResQuotaOverlay {
	if in == nil {
		return nil
	}
	out := new(ResQuotaOverlay)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Revision) DeepCopyInto(out *Revision) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Revision.
func (in *Revision) DeepCopy() *Revision {
	if in == nil {
		return nil
	}
	out := new(Revision)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *SvcDiscConfig) DeepCopyInto(out *SvcDiscConfig) {
	*out = *in
	if in.BkSaaS != nil {
		in, out := &in.BkSaaS, &out.BkSaaS
		*out = make([]SvcDiscEntryBkSaaS, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new SvcDiscConfig.
func (in *SvcDiscConfig) DeepCopy() *SvcDiscConfig {
	if in == nil {
		return nil
	}
	out := new(SvcDiscConfig)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *SvcDiscEntryBkSaaS) DeepCopyInto(out *SvcDiscEntryBkSaaS) {
	*out = *in
	if in.ModuleName != nil {
		in, out := &in.ModuleName, &out.ModuleName
		*out = new(string)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new SvcDiscEntryBkSaaS.
func (in *SvcDiscEntryBkSaaS) DeepCopy() *SvcDiscEntryBkSaaS {
	if in == nil {
		return nil
	}
	out := new(SvcDiscEntryBkSaaS)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *VolumeSource) DeepCopyInto(out *VolumeSource) {
	*out = *in
	if in.ConfigMap != nil {
		in, out := &in.ConfigMap, &out.ConfigMap
		*out = new(ConfigMapSource)
		**out = **in
	}
	if in.PersistentStorage != nil {
		in, out := &in.PersistentStorage, &out.PersistentStorage
		*out = new(PersistentStorage)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new VolumeSource.
func (in *VolumeSource) DeepCopy() *VolumeSource {
	if in == nil {
		return nil
	}
	out := new(VolumeSource)
	in.DeepCopyInto(out)
	return out
}
