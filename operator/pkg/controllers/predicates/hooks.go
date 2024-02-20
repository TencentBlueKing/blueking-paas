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

// NewHookSuccessPredicate create an GenericHookPredicate instance which will handle hook run successful event.
//
// This predicate will skip all other events unless the pod is changing to healthy. (healthy is meaning that the Pod is successfully complete or is Ready)
//   - With this predicate, any successful hook will wake up the bkapp reconciler.
//   - Only the pod state is changing to healthy will be handled, other update events will be ignored by this predicate
//     even the pod have already healthy.
func NewHookSuccessPredicate() predicate.Predicate {
	return &GenericHookPredicate{
		Logger: logf.Log,
		updateFunc: func(oldPod, newPod *corev1.Pod) bool {
			oldHealthStatus := kubestatus.CheckPodHealthStatus(oldPod)
			newHealthStatus := kubestatus.CheckPodHealthStatus(newPod)

			// the pod state is changing to ready
			return (oldHealthStatus.Phase != paasv1alpha2.HealthHealthy) &&
				(newHealthStatus.Phase == paasv1alpha2.HealthHealthy)
		},
	}
}

// NewHookFailedPredicate create an GenericHookPredicate instance which will handle hook run failed event.
//
// This predicate will skip all other events unless the pod is changing to unhealthy. (unhealthy is meaning that the Pod is restarting or is Failed)
//   - With this predicate, any failed hook will wake up the bkapp reconciler.
//   - Only the pod state is changing to unhealthy will be handled, other update events will be ignored by this predicate
//     even the pod have already unhealthy.
func NewHookFailedPredicate() predicate.Predicate {
	return &GenericHookPredicate{
		Logger: logf.Log,
		updateFunc: func(oldPod, newPod *corev1.Pod) bool {
			oldHealthStatus := kubestatus.CheckPodHealthStatus(oldPod)
			newHealthStatus := kubestatus.CheckPodHealthStatus(newPod)

			// the pod state is changing to not-ready
			return (oldHealthStatus.Phase != paasv1alpha2.HealthUnhealthy) &&
				(newHealthStatus.Phase == paasv1alpha2.HealthUnhealthy)
		},
	}
}

// GenericHookPredicate implements predicate functions on the Hook Pod status changed.
//
// This predicate will skip all other events not triggered by hook pod.
type GenericHookPredicate struct {
	predicate.Funcs

	Logger logr.Logger
	// updateFunc returns true if the Update event should be processed
	updateFunc func(oldPod, newPod *corev1.Pod) bool
}

// Update returns true if the Update event should be processed.
func (p GenericHookPredicate) Update(e event.UpdateEvent) bool {
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

	return p.updateFunc(oldPod, newPod)
}
