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

// Package hooks ...
package hooks

import (
	"context"
	"fmt"
	"slices"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	hookres "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/svcdisc"
	"bk.tencent.com/paas-app-operator/pkg/health"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// HookPodsHistoryLimit 最大保留的 Hook Pod 数量（单种类型）
const HookPodsHistoryLimit = 3

// NewHookReconciler will return a HookReconciler with given k8s client
func NewHookReconciler(client client.Client) *HookReconciler {
	return &HookReconciler{Client: client}
}

// HookReconciler 负责处理 Hook 相关的调和逻辑
type HookReconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile ...
func (r *HookReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	log := logf.FromContext(ctx)
	current := r.getCurrentState(ctx, bkapp)

	log.V(1).Info("handling pre-release-hook reconciliation")
	if current.Pod != nil {
		if err := r.UpdateStatus(bkapp, current, hookres.HookExecuteTimeoutThreshold); err != nil {
			return r.Result.WithError(err)
		}

		switch {
		case current.TimeoutExceededProgressing(hookres.HookExecuteTimeoutThreshold):
			// Pod 执行超时之后，终止调和循环
			return r.Result.End()
		case current.TimeoutExceededFailed(hookres.HookExecuteFailedTimeoutThreshold):
			// Pod 在超时时间内一直失败, 终止调和循环
			log.Error(errors.WithStack(hookres.ErrPodEndsUnsuccessfully), "execute timeout")
			// 不能调用 WithError 否则不会停止调和循环（Result 协议保持与 controller-runtime 的协议一致）
			// ref: https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.12.1/pkg/reconcile#Reconciler
			return r.Result.End()
		case current.Progressing():
			// 当 Hook 执行成功或失败时会由 owned pod 触发新的调和循环, 因此只需要通过 Requeue 处理超时事件即可
			return r.Result.Requeue(hookres.HookExecuteTimeoutThreshold)
		case current.Succeeded():
			return r.Result
		default:
			return r.Result.WithError(
				errors.Wrapf(hookres.ErrPodEndsUnsuccessfully, "hook failed with: %s", current.Status.Message),
			)
		}
	}

	// 对于过旧的 Pre-Release Hook Pod 进行清理
	if err := r.cleanupFinishedHooks(ctx, bkapp, paasv1alpha2.HookPreRelease); err != nil {
		return r.Result.WithError(err)
	}

	hook, err := hookres.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
	if err != nil {
		return r.Result.WithError(err)
	}
	if hook != nil {
		// Apply service discovery related changes
		if ok := svcdisc.NewWorkloadsMutator(r.Client, bkapp).ApplyToPod(ctx, hook.Pod); ok {
			log.V(1).Info("Applied svc-discovery related changes to the pre-release pod.")
		}

		if err = r.ExecuteHook(ctx, bkapp, hook); err != nil {
			return r.Result.WithError(err)
		}
		// 启动 Pod 后退出调和循环, 等待 Pod 状态更新事件触发下次循环
		return r.Result.End()
	}

	hookCond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.HooksFinished)
	var observedGeneration int64
	if hookCond != nil {
		observedGeneration = hookCond.ObservedGeneration
	} else {
		observedGeneration = bkapp.Generation
	}
	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.HooksFinished,
		Status:             metav1.ConditionUnknown,
		Reason:             "Disabled",
		Message:            "Pre-Release-Hook feature not turned on",
		ObservedGeneration: observedGeneration,
	})
	r.updateAppProgressingStatus(bkapp, metav1.ConditionTrue)

	return r.Result
}

// 获取应用当前在集群中的状态
func (r *HookReconciler) getCurrentState(ctx context.Context, bkapp *paasv1alpha2.BkApp) hookres.HookInstance {
	pod := corev1.Pod{}
	key := types.NamespacedName{Namespace: bkapp.Namespace, Name: names.PreReleaseHook(bkapp)}
	if err := r.Client.Get(ctx, key, &pod); err != nil {
		return hookres.HookInstance{
			Pod: nil,
			Status: &paasv1alpha2.HookStatus{
				Type:      paasv1alpha2.HookPreRelease,
				Started:   lo.ToPtr(false),
				StartTime: nil,
				Phase:     paasv1alpha2.HealthUnknown,
				Reason:    "Failed",
				Message:   lo.Ternary(apierrors.IsNotFound(err), "PreReleaseHook not found", err.Error()),
			},
		}
	}

	// NOTE: 最终返回的 Instance 状态并未完全使用该状态，仅仅只使用了“启动时间”，Instance 状态以 Pod 状态为准，
	currentStatus := bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease)
	// 如果创建 Pod 后未正常写入 Phase, 这里则重新写这个状态
	if currentStatus == nil {
		currentStatus = &paasv1alpha2.HookStatus{
			Type:      paasv1alpha2.HookPreRelease,
			Started:   lo.ToPtr(true),
			StartTime: lo.ToPtr(pod.GetCreationTimestamp()),
		}
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.HooksFinished,
			Status:             metav1.ConditionFalse,
			Reason:             "Progressing",
			Message:            "The pre-release hook is executing.",
			ObservedGeneration: bkapp.Generation,
		})
	}

	// StartTime 总是重新读取, 避免调和时, currentStatus.StartTime 仍是上一个 Instance 的 StartTime
	currentStatus.StartTime = lo.ToPtr(pod.GetCreationTimestamp())

	healthStatus := health.CheckPodHealthStatus(&pod)
	return hookres.HookInstance{
		Pod: &pod,
		Status: &paasv1alpha2.HookStatus{
			Type:      paasv1alpha2.HookPreRelease,
			Started:   currentStatus.Started,
			StartTime: currentStatus.StartTime,
			Phase:     healthStatus.Phase,
			Message:   healthStatus.Message,
			Reason:    healthStatus.Reason,
		},
	}
}

// ExecuteHook 执行 Hook
func (r *HookReconciler) ExecuteHook(
	ctx context.Context, bkapp *paasv1alpha2.BkApp, instance *hookres.HookInstance,
) error {
	pod := corev1.Pod{}
	// Only proceed when Pod resource is not found
	if err := r.Client.Get(ctx, client.ObjectKeyFromObject(instance.Pod), &pod); err == nil {
		return errors.WithStack(hookres.ErrHookPodExists)
	} else if !apierrors.IsNotFound(err) {
		return err
	}

	if err := r.Client.Create(ctx, instance.Pod); err != nil {
		return err
	}

	bkapp.Status.SetHookStatus(paasv1alpha2.HookStatus{
		Type:      paasv1alpha2.HookPreRelease,
		Started:   lo.ToPtr(true),
		StartTime: lo.ToPtr(metav1.Now()),
		Phase:     paasv1alpha2.HealthProgressing,
	})
	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.HooksFinished,
		Status:             metav1.ConditionFalse,
		Reason:             "Progressing",
		Message:            "The pre-release hook is executing.",
		ObservedGeneration: bkapp.Generation,
	})
	return nil
}

// UpdateStatus will update bkapp hook status from the given instance status
func (r *HookReconciler) UpdateStatus(
	bkapp *paasv1alpha2.BkApp,
	instance hookres.HookInstance,
	timeoutThreshold time.Duration,
) error {
	bkapp.Status.SetHookStatus(*instance.Status)

	hookCond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.HooksFinished)
	var observedGeneration int64
	if hookCond != nil {
		observedGeneration = hookCond.ObservedGeneration
	} else {
		observedGeneration = bkapp.Generation
	}

	// 若 Hook Pod 不存在，则应该判定 Hook 执行失败，但不认为 bkapp 失败，因为可以通过后续调和循环重新创建 Hook Pod
	if instance.Pod == nil {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.HooksFinished,
			Status:             metav1.ConditionFalse,
			Reason:             instance.Status.Reason,
			Message:            instance.Status.Message,
			ObservedGeneration: observedGeneration,
		})
		r.updateAppProgressingStatus(bkapp, metav1.ConditionFalse)
		return nil
	}

	switch {
	case instance.TimeoutExceededProgressing(timeoutThreshold):
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:   paasv1alpha2.HooksFinished,
			Status: metav1.ConditionFalse,
			Reason: "Failed",
			Message: fmt.Sprintf(
				"PreReleaseHook execute timeout, last message: %s",
				instance.Status.Message,
			),
			ObservedGeneration: observedGeneration,
		})
		r.updateAppProgressingStatus(bkapp, metav1.ConditionFalse)

	case instance.Succeeded():
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.HooksFinished,
			Status:             metav1.ConditionTrue,
			Reason:             "Finished",
			ObservedGeneration: observedGeneration,
		})
		r.updateAppProgressingStatus(bkapp, metav1.ConditionTrue)

	case instance.Failed():
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.HooksFinished,
			Status:             metav1.ConditionFalse,
			Reason:             "Failed",
			Message:            fmt.Sprintf("PreReleaseHook fail to succeed: %s", instance.Status.Message),
			ObservedGeneration: observedGeneration,
		})
		r.updateAppProgressingStatus(bkapp, metav1.ConditionFalse)
	}

	return nil
}

func (r *HookReconciler) updateAppProgressingStatus(bkapp *paasv1alpha2.BkApp, status metav1.ConditionStatus) {
	// 新部署时, 根据钩子执行结果, 更新 AppProgressing 的状态
	AppProgressingCond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.AppProgressing)
	if AppProgressingCond != nil && AppProgressingCond.Status == metav1.ConditionUnknown {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppProgressing,
			Status:             status,
			Reason:             "NewDeploy",
			ObservedGeneration: bkapp.Generation,
		})
	}
}

func (r *HookReconciler) cleanupFinishedHooks(
	ctx context.Context, bkapp *paasv1alpha2.BkApp, hookType paasv1alpha2.HookType,
) error {
	podList := &corev1.PodList{}
	err := r.Client.List(
		ctx,
		podList,
		client.InNamespace(bkapp.Namespace),
		client.MatchingLabels(labels.HookPodSelector(bkapp, hookType)),
	)
	if err != nil {
		return err
	}

	pods := podList.Items
	numToDelete := len(pods) - HookPodsHistoryLimit
	// 数量没有超过保留上限，不需要清理
	if numToDelete <= 0 {
		return nil
	}

	// 按照创建时间排序，清理掉最早的几个
	slices.SortFunc(pods, func(x, y corev1.Pod) int {
		if x.CreationTimestamp.Equal(&y.CreationTimestamp) {
			return strings.Compare(x.Name, y.Name)
		}
		return lo.Ternary(x.CreationTimestamp.Before(&y.CreationTimestamp), -1, 1)
	})

	for i := 0; i < numToDelete; i++ {
		if err = r.Client.Delete(ctx, &pods[i]); err != nil {
			metrics.IncDeleteOldestHookFailures(bkapp)
			return err
		}
	}
	return nil
}

// CheckAndUpdatePreReleaseHookStatus 检查并更新 PreReleaseHook 执行状态
func CheckAndUpdatePreReleaseHookStatus(
	ctx context.Context, cli client.Client, bkapp *paasv1alpha2.BkApp, timeout time.Duration,
) (succeed bool, err error) {
	r := NewHookReconciler(cli)
	instance := r.getCurrentState(ctx, bkapp)

	if err = r.UpdateStatus(bkapp, instance, timeout); err != nil {
		return false, err
	}

	switch {
	// 删除超时的 Pod
	case instance.TimeoutExceededProgressing(timeout):
		if err = cli.Delete(ctx, instance.Pod); err != nil {
			return false, err
		}
		return false, errors.WithStack(hookres.ErrExecuteTimeout)
	// 若 instance.Pod 为 nil，会判定为失败
	case instance.Failed():
		return false, errors.Wrapf(
			hookres.ErrPodEndsUnsuccessfully,
			"hook failed with: %s",
			instance.Status.Message,
		)
	}
	return instance.Succeeded(), nil
}
