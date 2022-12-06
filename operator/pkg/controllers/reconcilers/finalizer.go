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

package reconcilers

import (
	"context"
	"fmt"

	"github.com/getsentry/sentry-go"
	corev1 "k8s.io/api/core/v1"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
)

// BkappFinalizer 负责处理 finalize 相关的调和逻辑
type BkappFinalizer struct {
	client.Client
	Result Result
}

// Reconcile ...
func (r *BkappFinalizer) Reconcile(ctx context.Context, bkapp *v1alpha1.BkApp) Result {
	if !controllerutil.ContainsFinalizer(bkapp, v1alpha1.BkAppFinalizerName) || bkapp.DeletionTimestamp.IsZero() {
		return r.Result
	}

	log := logf.FromContext(ctx)
	log.Info("OnGarbageCollection")

	// our finalizer is present, so lets handle any external dependency
	finished, err := r.hooksFinished(ctx, bkapp)
	if err != nil {
		sentry.CaptureException(err)
		return r.Result.withError(fmt.Errorf("failed to check hook status: %w", err))
	}
	if !finished {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.AppAvailable,
			Status:             metav1.ConditionFalse,
			Reason:             "Terminating",
			Message:            "Deletion request was issued, but hooks are not finished.",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
		if err = r.Status().Update(ctx, bkapp); err != nil {
			sentry.CaptureException(err)
			return r.Result.withError(fmt.Errorf("failed to update condition status: %w", err))
		}
		return r.Result.requeue(v1alpha1.DefaultRequeueAfter)
	}
	if err = r.deleteResources(ctx, bkapp); err != nil {
		// if fail to delete the external dependency here, return with error
		// so that it can be retried
		sentry.CaptureException(err)
		return r.Result.withError(fmt.Errorf("failed to delete external resources: %w", err))
	}

	// remove our finalizer from the finalizers list and update it.
	controllerutil.RemoveFinalizer(bkapp, v1alpha1.BkAppFinalizerName)
	if err = r.Update(ctx, bkapp); err != nil {
		sentry.CaptureException(err)
		return r.Result.withError(fmt.Errorf("failed to remove finilizer for app: %w", err))
	}
	return r.Result.End()
}

// 检查是否所有 Hooks 都执行完毕
func (r *BkappFinalizer) hooksFinished(ctx context.Context, bkapp *v1alpha1.BkApp) (bool, error) {
	pods := &corev1.PodList{}
	err := r.List(ctx, pods,
		client.InNamespace(bkapp.Namespace),
		client.MatchingLabels{
			v1alpha1.BkAppNameKey:    bkapp.GetName(),
			v1alpha1.ResourceTypeKey: "hook",
		},
	)
	if err != nil {
		return false, err
	}

	for _, pod := range pods.Items {
		if pod.Status.Phase == corev1.PodRunning {
			return false, nil
		}
	}
	return true, nil
}

// deleteResources delete all related resources of BkApp object
func (r *BkappFinalizer) deleteResources(ctx context.Context, bkapp *v1alpha1.BkApp) error {
	var err error
	if err = r.deleteHookPods(ctx, bkapp); err != nil {
		return fmt.Errorf("failed to delete hook pods: %w", err)
	}
	if err = r.deleteServices(ctx, bkapp); err != nil {
		return fmt.Errorf("failed to delete services: %w", err)
	}
	return nil
}

func (r *BkappFinalizer) deleteHookPods(ctx context.Context, bkapp *v1alpha1.BkApp) error {
	// clean up all history hooks
	opts := []client.DeleteAllOfOption{
		client.InNamespace(bkapp.GetNamespace()),
		client.MatchingLabels{
			v1alpha1.BkAppNameKey:    bkapp.GetName(),
			v1alpha1.ResourceTypeKey: "hook",
		},
		client.GracePeriodSeconds(5),
	}
	return r.DeleteAllOf(ctx, &corev1.Pod{}, opts...)
}

func (r *BkappFinalizer) deleteServices(ctx context.Context, bkapp *v1alpha1.BkApp) error {
	// Delete individually instead of deleteCollection
	// issue: https://github.com/kubernetes/kubernetes/issues/68468
	svcList := corev1.ServiceList{}
	err := r.List(
		ctx,
		&svcList,
		client.InNamespace(bkapp.GetNamespace()),
		client.MatchingLabels{v1alpha1.BkAppNameKey: bkapp.GetName()},
	)
	if err != nil {
		return fmt.Errorf("failed to query ServiceList: %w", err)
	}
	for _, svc := range svcList.Items {
		if err = r.Delete(ctx, &svc); err != nil {
			return fmt.Errorf(
				"failed to delete Service(%s/%s) when finalizing the BkApp: %w",
				svc.GetNamespace(),
				svc.GetName(),
				err,
			)
		}
	}
	return nil
}
