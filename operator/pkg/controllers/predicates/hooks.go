package predicates

import (
	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/event"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/predicate"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubestatus"
)

// NewHookFinishedPredicate create an HookFinishedPredicate instance
func NewHookFinishedPredicate() predicate.Predicate {
	return &HookFinishedPredicate{
		Logger: logf.Log,
	}
}

// HookFinishedPredicate implements an update predicate function on the Hook Pod being ready.
//
// This predicate will skip all other events unless the pod state is change from not-ready to ready.
// * With this predicate, any successful hook will wake up the bkapp reconciler.
type HookFinishedPredicate struct {
	Logger logr.Logger
	predicate.Funcs
}

// Update implements UpdateEvent filter for validating whether the pod state is change from not-ready to ready.
func (p HookFinishedPredicate) Update(e event.UpdateEvent) bool {
	if e.ObjectOld == nil {
		p.Logger.Error(nil, "Update event has no old object to update", "event", e)
		return false
	}
	if e.ObjectNew == nil {
		p.Logger.Error(nil, "Update event has no new object for update", "event", e)
		return false
	}
	if e.ObjectNew.GetLabels()[paasv1alpha2.ResourceTypeKey] != "hook" {
		p.Logger.V(1).Info("Update event received from a pod that is not a hook, skip it", "event", e)
		return false
	}
	oldPod := e.ObjectOld.(*corev1.Pod)
	newPod := e.ObjectNew.(*corev1.Pod)
	oldHealthStatus := kubestatus.CheckPodHealthStatus(oldPod)
	newHealthStatus := kubestatus.CheckPodHealthStatus(newPod)

	// the pod state is change from not-ready to ready
	return (oldHealthStatus.Phase != paasv1alpha2.HealthHealthy) &&
		(newHealthStatus.Phase == paasv1alpha2.HealthHealthy)
}
