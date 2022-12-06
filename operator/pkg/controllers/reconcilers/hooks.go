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
	"time"

	"github.com/getsentry/sentry-go"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubestatus"
)

// HookReconciler 负责处理 Hook 相关的调和逻辑
type HookReconciler struct {
	client.Client
	Result Result
}

// Reconcile ...
func (r *HookReconciler) Reconcile(ctx context.Context, bkapp *v1alpha1.BkApp) Result {
	log := logf.FromContext(ctx)
	current := r.getCurrentState(ctx, bkapp)

	log.V(4).Info("handling pre-release-hook reconciliation")
	if current.Pod != nil {
		if err := r.UpdateStatus(ctx, bkapp, current, resources.HookExecuteTimeoutThreshold); err != nil {
			sentry.CaptureException(err)
			return r.Result.withError(err)
		}

		// TODO: timeout 或者 failed 是否直接终止整个调和循环？因为重新入队后下次调和循环也不可能成功
		// TODO: 确定 kubebuilder 失败重试次数的阈值
		switch {
		case current.Timeout(resources.HookExecuteTimeoutThreshold):
			// 删除超时的 pod
			if err := r.Delete(ctx, current.Pod); err != nil {
				sentry.CaptureException(err)
				return r.Result.withError(resources.ErrExecuteTimeout)
			}
			return r.Result.withError(resources.ErrExecuteTimeout)
		case current.Progressing():
			return r.Result.requeue(v1alpha1.DefaultRequeueAfter)
		case current.Succeeded():
			return r.Result
		default:
			return r.Result.withError(
				fmt.Errorf("%w: hook failed with: %s", resources.ErrPodEndsUnsuccessfully, current.Status.Message),
			)
		}
	}

	if hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease)); hook != nil {
		if err := r.ExecuteHook(ctx, bkapp, hook); err != nil {
			sentry.CaptureException(err)
			return r.Result.withError(err)
		}
		// 启动 Pod 后退出调和循环, 等待 Pod 状态更新事件触发下次循环
		return r.Result.End()
	}

	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               v1alpha1.HooksFinished,
		Status:             metav1.ConditionUnknown,
		Reason:             "Disabled",
		Message:            "Pre-Release-Hook feature not turned on",
		ObservedGeneration: bkapp.Status.ObservedGeneration,
	})
	if err := r.Status().Update(ctx, bkapp); err != nil {
		sentry.CaptureException(err)
		return r.Result.withError(err)
	}
	return r.Result
}

// 获取应用当前在集群中的状态
func (r *HookReconciler) getCurrentState(ctx context.Context, bkapp *v1alpha1.BkApp) resources.HookInstance {
	currentStatus := bkapp.Status.FindHookStatus(v1alpha1.HookPreRelease)
	pod := corev1.Pod{}
	err := r.Get(ctx, types.NamespacedName{Name: names.PreReleaseHook(bkapp), Namespace: bkapp.Namespace}, &pod)
	if err != nil {
		return resources.HookInstance{
			Pod:    nil,
			Status: nil,
		}
	}

	// 如果创建 Pod 后未正常写入 Status, 这里则重新写这个状态
	if currentStatus == nil {
		currentStatus = &v1alpha1.HookStatus{
			Type:      v1alpha1.HookPreRelease,
			Started:   lo.ToPtr(true),
			StartTime: lo.ToPtr(pod.GetCreationTimestamp()),
		}
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.HooksFinished,
			Status:             metav1.ConditionFalse,
			Reason:             "Progressing",
			Message:            "The pre-release hook is executing.",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	}

	healthStatus := kubestatus.CheckPodHealthStatus(&pod)
	return resources.HookInstance{
		Pod: &pod,
		Status: &v1alpha1.HookStatus{
			Type:      v1alpha1.HookPreRelease,
			Started:   currentStatus.Started,
			StartTime: currentStatus.StartTime,
			Status:    healthStatus.Status,
			Message:   healthStatus.Message,
			Reason:    healthStatus.Reason,
		},
	}
}

// ExecuteHook 执行 Hook
func (r *HookReconciler) ExecuteHook(
	ctx context.Context, bkapp *v1alpha1.BkApp, instance *resources.HookInstance,
) error {
	pod := corev1.Pod{}
	// Only proceed when Pod resource is not found
	if err := r.Get(ctx, client.ObjectKeyFromObject(instance.Pod), &pod); err == nil {
		return resources.ErrHookPodExists
	} else if !apierrors.IsNotFound(err) {
		return err
	}

	err := r.Create(ctx, instance.Pod)
	if err != nil {
		return err
	}

	bkapp.Status.SetHookStatus(v1alpha1.HookStatus{
		Type:      v1alpha1.HookPreRelease,
		Started:   lo.ToPtr(true),
		StartTime: lo.ToPtr(metav1.Now()),
		Status:    v1alpha1.HealthProgressing,
	})
	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               v1alpha1.HooksFinished,
		Status:             metav1.ConditionFalse,
		Reason:             "Progressing",
		Message:            "The pre-release hook is executing.",
		ObservedGeneration: bkapp.Status.ObservedGeneration,
	})
	return r.Status().Update(ctx, bkapp)
}

// UpdateStatus will update bkapp hook status from the given instance status
func (r *HookReconciler) UpdateStatus(
	ctx context.Context,
	bkapp *v1alpha1.BkApp,
	instance resources.HookInstance,
	timeoutThreshold time.Duration,
) error {
	bkapp.Status.SetHookStatus(*instance.Status)
	switch {
	case instance.Timeout(timeoutThreshold):
		bkapp.Status.Phase = v1alpha1.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:   v1alpha1.HooksFinished,
			Status: metav1.ConditionFalse,
			Reason: "Failed",
			Message: fmt.Sprintf(
				"PreReleaseHook execute timeout, last message: %s",
				instance.Status.Message,
			),
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	case instance.Succeeded():
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.HooksFinished,
			Status:             metav1.ConditionTrue,
			Reason:             "Finished",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	case instance.Failed():
		bkapp.Status.Phase = v1alpha1.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.HooksFinished,
			Status:             metav1.ConditionFalse,
			Reason:             "Failed",
			Message:            fmt.Sprintf("PreReleaseHook fail to succeed: %s", instance.Status.Message),
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	}
	return r.Status().Update(ctx, bkapp)
}

// CheckAndUpdatePreReleaseHookStatus 检查并更新 PreReleaseHook 执行状态
func CheckAndUpdatePreReleaseHookStatus(
	ctx context.Context, cli client.Client, bkapp *v1alpha1.BkApp, timeout time.Duration,
) (succeed bool, err error) {
	r := HookReconciler{Client: cli}
	instance := r.getCurrentState(ctx, bkapp)

	if instance.Pod == nil {
		return false, fmt.Errorf("pre-release-hook not found")
	}

	if err = r.UpdateStatus(ctx, bkapp, instance, timeout); err != nil {
		return false, err
	}

	switch {
	// 删除超时的 pod
	case instance.Timeout(timeout):
		if err = cli.Delete(ctx, instance.Pod); err != nil {
			return false, err
		}
		return false, resources.ErrExecuteTimeout
	case instance.Failed():
		return false, fmt.Errorf(
			"%w: hook failed with: %s",
			resources.ErrPodEndsUnsuccessfully,
			instance.Status.Message,
		)
	}
	return instance.Succeeded(), nil
}
