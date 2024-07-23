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

package bkapp

import (
	"context"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	hookres "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks/resources"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// NewBkappFinalizer will return a BkappFinalizer with given k8s client
func NewBkappFinalizer(client client.Client) *BkappFinalizer {
	return &BkappFinalizer{Client: client}
}

// BkappFinalizer 负责处理 finalize 相关的调和逻辑
type BkappFinalizer struct {
	Client client.Client
	Result base.Result
}

// Reconcile ...
func (r *BkappFinalizer) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	if !controllerutil.ContainsFinalizer(bkapp, paasv1alpha2.BkAppFinalizerName) || bkapp.DeletionTimestamp.IsZero() {
		return r.Result
	}

	log := logf.FromContext(ctx)
	log.Info("OnGarbageCollection", "bkapp", bkapp.Name)

	// our finalizer is present, so lets handle any external dependency
	canFinalizeHooks, err := r.allHooksFinishedOrTimeout(ctx, bkapp)
	if err != nil {
		metrics.IncHooksFinishedFailures(bkapp)
		return r.Result.WithError(errors.Wrapf(err, "failed to check hook status for bkapp %s/%s", bkapp.Namespace, bkapp.Name))
	}
	if !canFinalizeHooks {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppAvailable,
			Status:             metav1.ConditionFalse,
			Reason:             "Terminating",
			Message:            "Deletion request was issued, but hooks are not canFinalizeHooks.",
			ObservedGeneration: bkapp.Generation,
		})
		return r.Result.Requeue(paasv1alpha2.DefaultRequeueAfter)
	}
	if err = r.deleteResources(ctx, bkapp); err != nil {
		metrics.IncDeleteResourcesFailures(bkapp)
		// if fail to delete the external dependency here, return with error
		// so that it can be retried
		return r.Result.WithError(errors.Wrap(err, "failed to delete external resources"))
	}

	// remove our finalizer from the finalizers list and update it.
	controllerutil.RemoveFinalizer(bkapp, paasv1alpha2.BkAppFinalizerName)
	if err = r.Client.Update(ctx, bkapp); err != nil {
		return r.Result.WithError(errors.Wrap(err, "failed to remove finalizer for app"))
	}
	return r.Result.End()
}

// allHooksFinishedOrTimeout 检查是否所有 Hooks 都执行完毕或执行超时
func (r *BkappFinalizer) allHooksFinishedOrTimeout(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) (bool, error) {
	log := logf.FromContext(ctx)
	pods := &corev1.PodList{}
	err := r.Client.List(
		ctx, pods,
		client.InNamespace(bkapp.Namespace),
		client.MatchingLabels{
			paasv1alpha2.BkAppNameKey:    bkapp.GetName(),
			paasv1alpha2.ResourceTypeKey: "hook",
		},
	)
	if err != nil {
		return false, err
	}

	// 检查 PodList 里是否有仍然在执行中的 Pod
	anyRunning := lo.ContainsBy(pods.Items, func(pod corev1.Pod) bool {
		if pod.Status.Phase == corev1.PodRunning {
			if isPodExecTimeout(pod, hookres.HookExecuteTimeoutThreshold) {
				log.V(1).Info("pod have executed timeout, ignore", "pod-name", pod.GetName())
				return false
			}
			return true
		}
		return false
	})
	return !anyRunning, nil
}

// isPodExecTimeout 检查 pod 的运行时间是否超过阈值
func isPodExecTimeout(pod corev1.Pod, timeout time.Duration) bool {
	return !pod.Status.StartTime.IsZero() &&
		pod.Status.StartTime.Add(timeout).Before(time.Now())
}

// deleteResources delete all related resources of BkApp object
func (r *BkappFinalizer) deleteResources(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	var err error
	if err = r.deleteHookPods(ctx, bkapp); err != nil {
		return errors.Wrap(err, "failed to delete hook pods")
	}
	if err = r.deleteServices(ctx, bkapp); err != nil {
		return errors.Wrap(err, "failed to delete services")
	}
	return nil
}

func (r *BkappFinalizer) deleteHookPods(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	// clean up all history hooks
	opts := []client.DeleteAllOfOption{
		client.InNamespace(bkapp.GetNamespace()),
		client.MatchingLabels{
			paasv1alpha2.BkAppNameKey:    bkapp.GetName(),
			paasv1alpha2.ResourceTypeKey: "hook",
		},
		client.GracePeriodSeconds(5),
	}
	return r.Client.DeleteAllOf(ctx, &corev1.Pod{}, opts...)
}

func (r *BkappFinalizer) deleteServices(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	// Delete individually instead of deleteCollection
	// issue: https://github.com/kubernetes/kubernetes/issues/68468
	svcList := corev1.ServiceList{}
	err := r.Client.List(
		ctx,
		&svcList,
		client.InNamespace(bkapp.GetNamespace()),
		client.MatchingLabels{paasv1alpha2.BkAppNameKey: bkapp.GetName()},
	)
	if err != nil {
		return errors.Wrap(err, "failed to query ServiceList")
	}
	for _, svc := range svcList.Items {
		if err = r.Client.Delete(ctx, &svc); err != nil {
			return errors.Wrapf(
				err, "failed to delete Service(%s/%s) when finalizing the BkApp", svc.GetNamespace(), svc.GetName(),
			)
		}
	}
	return nil
}
