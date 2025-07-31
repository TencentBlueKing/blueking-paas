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

// Package bkapp provides reconciler helps initialize the status of
// the BkApp when a new deploy action is issued.
package bkapp

import (
	"context"
	"fmt"

	"github.com/pkg/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks"
	hookres "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/hooks/resources"
	procres "bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/resources"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
	platdeploy "bk.tencent.com/paas-app-operator/pkg/platform/deploy"
)

// NewDeployActionReconciler returns a DeployActionReconciler.
func NewDeployActionReconciler(client client.Client) *DeployActionReconciler {
	return &DeployActionReconciler{Client: client}
}

// DeployActionReconciler reconcile the statuses when a new deploy action has been
// detected.
type DeployActionReconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile reconciles.
func (r *DeployActionReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	log := logf.FromContext(ctx)
	var err error
	log.V(1).Info(fmt.Sprintf("handling deploy action reconciliation for bkapp %s/%s", bkapp.Namespace, bkapp.Name))

	currentDeployID := bkapp.Annotations[paasv1alpha2.DeployIDAnnoKey]
	if currentDeployID == "" {
		currentDeployID = procres.DefaultDeployID
	}

	// When the deploy id in the status is the same with the value in the annotations,
	// it means that there is no new deploy action, the further process of current reconcile
	// loop wil be skipped.
	if bkapp.Status.DeployId == currentDeployID {
		log.V(1).Info(
			"No new deploy action found on the BkApp, skip the rest of the process",
			"ObservedGeneration",
			bkapp.Status.ObservedGeneration,
			"Generation",
			bkapp.Generation,
		)
		return r.Result
	}

	// If this is not the initial deploy action, check if there is any preceding running hooks,
	// wait for these hooks by return an error to delay for another reconcile cycle.
	//
	// If hook already turned off, validateNoRunningHooks should not execute (disregarding previous hooks).
	if bkapp.Spec.Hooks != nil && bkapp.Status.DeployId != "" {
		if err = r.validateNoRunningHooks(ctx, bkapp); err != nil {
			return r.Result.WithError(err)
		}
	}

	log.Info("New deploy action found", "name", bkapp.Name, "deployID", currentDeployID)
	bkapp.Status.Phase = paasv1alpha2.AppPending
	bkapp.Status.SetDeployID(currentDeployID)
	SetDefaultConditions(bkapp)

	// deep copy bkapp to generate merge-patch
	originalBkapp := bkapp.DeepCopy()
	// clear original bkapp status to force update
	originalBkapp.Status = paasv1alpha2.AppStatus{
		// 必须保留 HookStatuses 字段值, 目的是在 MergeFrom 时, 对比 bkapp.Status.HookStatuses 与
		// originalBkapp.Status.HookStatuses 的值, 生成 patch 指令, 清空集群内 bkapp 模型的 HookStatuses 字段.
		// 清空后, 进一步避免了在 HookReconciler 中, 读取到旧 HookStatuses 的情况.
		// 有关 MergeFrom 的说明: https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/client#MergeFrom
		HookStatuses: bkapp.Status.HookStatuses,
	}
	bkapp.Status.HookStatuses = nil

	if err = r.Client.Status().Patch(ctx, bkapp, client.MergeFrom(originalBkapp)); err != nil {
		metrics.IncDeployActionUpdateBkappStatusFailures(bkapp)
		return r.Result.WithError(
			errors.Wrapf(err, "update bkapp %s status when a new deploy action is detected", bkapp.Name),
		)
	}
	return r.Result
}

// validate that there are no running hooks currently, return error if found any running hooks.
func (r *DeployActionReconciler) validateNoRunningHooks(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	// 如果上一次的部署是被用户主动中断, 则继续执行后续的部署调和流程, 忽略可能处于 progressing 状态的旧 hook
	// TODO 考虑支持更实时的中断请求, 包括直接删除执行中的 hook 等?
	if platdeploy.GetLastDeployStatus(bkapp) == "interrupted" {
		return nil
	}
	// Check pre-release hook
	if hookres.IsPreReleaseProgressing(bkapp) {
		_, err := hooks.CheckAndUpdatePreReleaseHookStatus(
			ctx,
			r.Client,
			bkapp,
			hookres.HookExecuteTimeoutThreshold,
		)
		if err != nil {
			return err
		}
		return errors.WithStack(hookres.ErrLastHookStillRunning)
	}
	return nil
}

// SetDefaultConditions set all conditions to initial value
func SetDefaultConditions(bkapp *paasv1alpha2.BkApp) {
	status := &bkapp.Status

	latestAvailableCond := apimeta.FindStatusCondition(status.Conditions, paasv1alpha2.AppAvailable)
	if latestAvailableCond == nil {
		apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AppAvailable,
			Status:             metav1.ConditionFalse,
			Reason:             "NewDeploy",
			Message:            "First time deployment, service unavailable",
			ObservedGeneration: bkapp.Generation,
		})
	}

	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AppProgressing,
		Status:             metav1.ConditionUnknown,
		Reason:             "NewDeploy",
		ObservedGeneration: bkapp.Generation,
	})
	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AddOnsProvisioned,
		Status:             metav1.ConditionUnknown,
		Reason:             "Initial",
		ObservedGeneration: bkapp.Generation,
	})
	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.HooksFinished,
		Status:             metav1.ConditionUnknown,
		Reason:             "Initial",
		ObservedGeneration: bkapp.Generation,
	})
}
