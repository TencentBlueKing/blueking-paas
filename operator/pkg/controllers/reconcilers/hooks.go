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
	"sort"
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
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubestatus"
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
	Result Result
}

// Reconcile ...
func (r *HookReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result {
	log := logf.FromContext(ctx)
	current := r.getCurrentState(ctx, bkapp)

	log.V(1).Info("handling pre-release-hook reconciliation")
	if current.Pod != nil {
		if err := r.UpdateStatus(ctx, bkapp, current, resources.HookExecuteTimeoutThreshold); err != nil {
			return r.Result.WithError(err)
		}

		switch {
		case current.Timeout(resources.HookExecuteTimeoutThreshold):
			// 删除超时的 pod
			if err := r.Client.Delete(ctx, current.Pod); err != nil {
				return r.Result.WithError(errors.WithStack(resources.ErrExecuteTimeout))
			}
			return r.Result.WithError(errors.WithStack(resources.ErrExecuteTimeout))
		case current.Progressing():
			return r.Result.requeue(paasv1alpha2.DefaultRequeueAfter)
		case current.Succeeded():
			return r.Result
		case current.FailedUntilTimeout(resources.HookExecuteFailedTimeoutThreshold):
			if err := r.Client.Delete(ctx, current.Pod); err != nil {
				return r.Result.WithError(errors.WithStack(resources.ErrPodEndsUnsuccessfully))
			}
			// Pod 在超时时间内一直失败, 终止调和循环
			return r.Result.WithError(errors.WithStack(resources.ErrPodEndsUnsuccessfully)).End()
		default:
			return r.Result.WithError(
				errors.Wrapf(resources.ErrPodEndsUnsuccessfully, "hook failed with: %s", current.Status.Message),
			)
		}
	}

	// 对于过旧的 Pre-Release Hook Pod 进行清理
	if err := r.cleanupFinishedHooks(ctx, bkapp, paasv1alpha2.HookPreRelease); err != nil {
		return r.Result.WithError(err)
	}

	hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
	if hook != nil {
		if err := r.ExecuteHook(ctx, bkapp, hook); err != nil {
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
func (r *HookReconciler) getCurrentState(ctx context.Context, bkapp *paasv1alpha2.BkApp) resources.HookInstance {
	pod := corev1.Pod{}
	err := r.Client.Get(ctx, types.NamespacedName{Name: names.PreReleaseHook(bkapp), Namespace: bkapp.Namespace}, &pod)
	if err != nil {
		return resources.HookInstance{
			Pod:    nil,
			Status: nil,
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

	healthStatus := kubestatus.CheckPodHealthStatus(&pod)
	return resources.HookInstance{
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
	ctx context.Context, bkapp *paasv1alpha2.BkApp, instance *resources.HookInstance,
) error {
	pod := corev1.Pod{}
	// Only proceed when Pod resource is not found
	if err := r.Client.Get(ctx, client.ObjectKeyFromObject(instance.Pod), &pod); err == nil {
		return errors.WithStack(resources.ErrHookPodExists)
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
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
	instance resources.HookInstance,
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

	switch {
	case instance.Timeout(timeoutThreshold):
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
		ctx, podList, client.InNamespace(bkapp.Namespace), client.MatchingLabels(labels.Hook(bkapp, hookType)),
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
	sort.Sort(byPodCreationTimestamp(pods))
	for i := 0; i < numToDelete; i++ {
		if err = r.Client.Delete(ctx, &pods[i]); err != nil {
			metrics.IncDeleteOldestHookFailures(bkapp, pods[i].Name)
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

	if instance.Pod == nil {
		return false, errors.New("pre-release-hook not found")
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
		return false, errors.WithStack(resources.ErrExecuteTimeout)
	case instance.Failed():
		return false, errors.Wrapf(
			resources.ErrPodEndsUnsuccessfully,
			"hook failed with: %s",
			instance.Status.Message,
		)
	}
	return instance.Succeeded(), nil
}
