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

package processes

import (
	"context"
	"fmt"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/components"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/resources"
)

const (
	// defaultSandboxRuntimeClassName is the default runtime class for sandbox instances
	defaultSandboxRuntimeClassName = "cube"
	// defaultSandboxNetworkMode is the default network mode
	defaultSandboxNetworkMode = "direct-cni"
	// defaultSandboxWebProcessName is the process name for AI Agent apps
	defaultSandboxWebProcessName = "web"
)

// NewSandboxInstanceReconciler creates a new SandboxInstanceReconciler
func NewSandboxInstanceReconciler(client client.Client) *SandboxInstanceReconciler {
	return &SandboxInstanceReconciler{Client: client}
}

// SandboxInstanceReconciler reconciles SandboxInstance CR for BkApps with workloadType=sandboxInstance.
// When a BkApp declares workloadType=sandboxInstance, this reconciler creates/updates a SandboxInstance CR
// instead of a Deployment. The SandboxInstance is then rendered into a cube MicroVM Pod by
// the sandbox-controller.
type SandboxInstanceReconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile handles SandboxInstance lifecycle for isolated BkApps.
func (r *SandboxInstanceReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	log := logf.FromContext(ctx)

	// Only handle isolated deploy policy
	if bkapp.Spec.WorkloadType != paasv1alpha2.WorkloadTypeSandboxInstance {
		return r.Result
	}

	// Build the desired SandboxInstance
	desired, err := r.buildSandboxInstance(ctx, bkapp)
	if err != nil {
		return r.Result.WithError(errors.Wrap(err, "build sandbox instance"))
	}

	// Try to get existing SandboxInstance
	existing := &sandboxv1beta1.SandboxInstance{}
	err = r.Client.Get(ctx, types.NamespacedName{
		Name:      desired.Name,
		Namespace: desired.Namespace,
	}, existing)

	if err != nil {
		if apimeta.IsNoMatchError(err) {
			return r.handleCRDUnavailable(bkapp)
		}
		if client.IgnoreNotFound(err) != nil {
			return r.Result.WithError(errors.Wrap(err, "get sandbox instance"))
		}
		// Not found, create it
		log.Info("Creating SandboxInstance", "name", desired.Name)
		if err = r.Client.Create(ctx, desired); err != nil {
			return r.Result.WithError(errors.Wrap(err, "create sandbox instance"))
		}
	} else {
		// Update if spec changed
		if err = r.updateSandboxInstance(ctx, existing, desired); err != nil {
			return r.Result.WithError(errors.Wrap(err, "update sandbox instance"))
		}
	}

	// Refresh the SandboxInstance status to update BkApp status
	if err = r.Client.Get(ctx, types.NamespacedName{
		Name:      desired.Name,
		Namespace: desired.Namespace,
	}, existing); err != nil {
		return r.Result.WithError(errors.Wrap(err, "refresh sandbox instance status"))
	}

	// Map SandboxInstance phase to BkApp status
	r.updateBkAppStatus(bkapp, existing)

	if bkapp.Status.Phase == paasv1alpha2.AppPending {
		return r.Result.Requeue(paasv1alpha2.DefaultRequeueAfter)
	}
	return r.Result
}

// handleCRDUnavailable marks the BkApp as Failed when SandboxInstance CRD is not installed.
func (r *SandboxInstanceReconciler) handleCRDUnavailable(bkapp *paasv1alpha2.BkApp) base.Result {
	bkapp.Status.Phase = paasv1alpha2.AppFailed
	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AppAvailable,
		Status:             metav1.ConditionFalse,
		Reason:             "SandboxInstanceUnavailable",
		Message:            "SandboxInstance CRD is not installed in the cluster",
		ObservedGeneration: bkapp.Generation,
	})
	return r.Result
}

// buildSandboxInstance constructs the desired SandboxInstance CR from BkApp spec.
func (r *SandboxInstanceReconciler) buildSandboxInstance(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) (*sandboxv1beta1.SandboxInstance, error) {
	proc, err := r.resolveProcess(bkapp)
	if err != nil {
		return nil, err
	}

	container := r.buildMainContainer(ctx, bkapp, proc)
	podLabels := labels.Workload(bkapp, proc.Name)

	// Build the SandboxInstance
	sbi := &sandboxv1beta1.SandboxInstance{
		TypeMeta: metav1.TypeMeta{
			APIVersion: sandboxv1beta1.GroupVersion.String(),
			Kind:       "SandboxInstance",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      names.Workload(bkapp, proc.Name),
			Namespace: bkapp.Namespace,
			Labels:    podLabels,
			Annotations: map[string]string{
				paasv1alpha2.DeployIDAnnoKey: bkapp.Status.DeployId,
			},
			OwnerReferences: []metav1.OwnerReference{
				*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
					Group:   paasv1alpha2.GroupVersion.Group,
					Version: paasv1alpha2.GroupVersion.Version,
					Kind:    paasv1alpha2.KindBkApp,
				}),
			},
		},
		Spec: sandboxv1beta1.SandboxInstanceSpec{
			DesiredState:     sandboxv1beta1.SandboxDesiredStateRunning,
			RuntimeClassName: defaultSandboxRuntimeClassName,
			Network: sandboxv1beta1.SandboxNetwork{
				Mode: defaultSandboxNetworkMode,
			},
			// domain 保留为空，由 sandbox controller 计算 guest 的 cpu/memory
			Domain: sandboxv1beta1.SandboxDomain{},
			PodTemplate: sandboxv1beta1.SandboxPodTemplate{
				Containers:       []corev1.Container{container},
				NodeSelector:     common.BuildNodeSelector(bkapp),
				Tolerations:      common.BuildTolerations(bkapp),
				DNSConfig:        buildDNSConfigForSandbox(bkapp),
				HostAliases:      buildHostAliasesForSandbox(bkapp),
				ImagePullSecrets: common.BuildImagePullSecrets(bkapp),
				Labels:           podLabels,
			},
		},
	}

	// patch components to sandboxinstance
	if err = components.PatchToSandboxInstance(proc, sbi); err != nil {
		return nil, errors.Wrap(err, "patch components to SandboxInstance")
	}

	return sbi, nil
}

// resolveProcess finds the target process from BkApp spec.
// It prefers the "web" process, falling back to the first defined process.
func (r *SandboxInstanceReconciler) resolveProcess(
	bkapp *paasv1alpha2.BkApp,
) (*paasv1alpha2.Process, error) {
	proc := bkapp.Spec.FindProcess(defaultSandboxWebProcessName)
	if proc == nil && len(bkapp.Spec.Processes) > 0 {
		proc = &bkapp.Spec.Processes[0]
	}
	if proc == nil {
		return nil, errors.New("no process defined in BkApp")
	}
	return proc, nil
}

// buildMainContainer constructs the main container spec from process definition.
func (r *SandboxInstanceReconciler) buildMainContainer(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
	proc *paasv1alpha2.Process,
) corev1.Container {
	log := logf.FromContext(ctx)

	// Get resource requirements (CPU/Memory)
	resGetter := envs.NewProcResourcesGetter(bkapp)
	resReq, err := resGetter.GetByProc(proc.Name)
	if err != nil {
		log.Info("Failed to get resources for process, use default values",
			"process", proc.Name, "bkapp", bkapp.Name, "error", err)
		resReq = resGetter.Default()
	}

	// Get image
	image, pullPolicy, err := paasv1alpha2.NewProcImageGetter(bkapp).Get(proc.Name)
	if err != nil {
		log.Info("Failed to get image for process, use default values",
			"process", proc.Name, "bkapp", bkapp.Name, "error", err)
		image = resources.DefaultImage
		pullPolicy = corev1.PullIfNotPresent
	}

	// Build environment variables
	envVars := common.GetAppEnvs(bkapp)
	envVars = common.RenderAppVars(envVars, common.VarsRenderContext{ProcessType: proc.Name})

	return corev1.Container{
		Name:            proc.Name,
		Image:           image,
		ImagePullPolicy: pullPolicy,
		Env:             envVars,
		Command:         proc.Command,
		Args:            proc.Args,
		Resources:       resReq,
	}
}

// updateSandboxInstance patches the existing SandboxInstance if the desired spec differs.
func (r *SandboxInstanceReconciler) updateSandboxInstance(
	ctx context.Context,
	existing *sandboxv1beta1.SandboxInstance,
	desired *sandboxv1beta1.SandboxInstance,
) error {
	// Update spec and annotations
	existing.Spec = desired.Spec
	existing.Annotations = desired.Annotations
	existing.Labels = desired.Labels
	return r.Client.Update(ctx, existing)
}

// updateBkAppStatus maps SandboxInstance phase to BkApp status conditions.
func (r *SandboxInstanceReconciler) updateBkAppStatus(bkapp *paasv1alpha2.BkApp, sbi *sandboxv1beta1.SandboxInstance) {
	phase := sbi.Status.Phase
	message := sbi.Status.Message

	switch phase {
	case sandboxv1beta1.SandboxPhaseRunning:
		bkapp.Status.Phase = paasv1alpha2.AppRunning
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppAvailable,
			Status:             metav1.ConditionTrue,
			Reason:             "SandboxRunning",
			Message:            lo.Ternary(message != "", message, "SandboxInstance is running"),
			ObservedGeneration: bkapp.Generation,
		})
	case sandboxv1beta1.SandboxPhaseFailed:
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppAvailable,
			Status:             metav1.ConditionFalse,
			Reason:             "SandboxFailed",
			Message:            lo.Ternary(message != "", message, "SandboxInstance failed"),
			ObservedGeneration: bkapp.Generation,
		})
	default:
		// Pending, Creating, Stopping, Stopped, Terminating
		bkapp.Status.Phase = paasv1alpha2.AppPending
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:   paasv1alpha2.AppAvailable,
			Status: metav1.ConditionFalse,
			Reason: "SandboxProgressing",
			Message: lo.Ternary(
				message != "",
				message,
				fmt.Sprintf("SandboxInstance is in phase: %s", lo.Ternary(phase != "", phase, "Unknown")),
			),
			ObservedGeneration: bkapp.Generation,
		})
	}
}

// buildDNSConfigForSandbox builds DNS config from BkApp's domainResolution
func buildDNSConfigForSandbox(bkapp *paasv1alpha2.BkApp) *corev1.PodDNSConfig {
	if bkapp.Spec.DomainResolution == nil {
		return nil
	}
	if len(bkapp.Spec.DomainResolution.Nameservers) == 0 {
		return nil
	}
	return &corev1.PodDNSConfig{
		Nameservers: bkapp.Spec.DomainResolution.Nameservers,
	}
}

// buildHostAliasesForSandbox builds host aliases from BkApp's domainResolution
func buildHostAliasesForSandbox(bkapp *paasv1alpha2.BkApp) []corev1.HostAlias {
	if bkapp.Spec.DomainResolution == nil {
		return nil
	}
	aliases := make([]corev1.HostAlias, 0, len(bkapp.Spec.DomainResolution.HostAliases))
	for _, ha := range bkapp.Spec.DomainResolution.HostAliases {
		aliases = append(aliases, corev1.HostAlias{
			IP:        ha.IP,
			Hostnames: ha.Hostnames,
		})
	}
	return aliases
}
