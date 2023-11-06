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

// This reconciler helps initialize the status of the BkApp when a new deploy action
// is issued.
package reconcilers

import (
	"context"

	"github.com/pkg/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
)

// NewDeployActionReconciler returns a DeployActionReconciler.
func NewDeployActionReconciler(client client.Client) *DeployActionReconciler {
	return &DeployActionReconciler{Client: client}
}

// DeployActionReconciler reconcile the statuses when a new deploy action has been
// detected.
type DeployActionReconciler struct {
	Client client.Client
	Result Result
}

// Reconcile reconciles.
func (r *DeployActionReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result {
	log := logf.FromContext(ctx)
	var err error
	log.V(4).Info("handling deploy action reconciliation.")

	currentDeployID := bkapp.Annotations[paasv1alpha2.DeployIDAnnoKey]
	if currentDeployID == "" {
		currentDeployID = resources.DefaultDeployID
	}

	// Check if the current deploy ID has been processed already.
	if bkapp.Status.ObservedGeneration >= bkapp.Generation || bkapp.Status.DeployId == currentDeployID {
		log.V(2).Info(
			"No new deploy action found on the BkApp, skip the rest of the process.",
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
	// TODO: Should we remove this logic and allow every new deploy action to start even the
	// hook triggered by older deploy is not finished yet?
	if bkapp.Status.DeployId != "" {
		if err = r.validateNoRunningHooks(ctx, bkapp); err != nil {
			return r.Result.withError(err)
		}
	}

	log.Info("New deploy action found.", "name", bkapp.Name, "deployID", currentDeployID)
	bkapp.Status.Phase = paasv1alpha2.AppPending
	bkapp.Status.HookStatuses = nil
	bkapp.Status.ObservedGeneration = bkapp.Generation
	bkapp.Status.SetDeployID(currentDeployID)
	SetDefaultConditions(&bkapp.Status)

	if err = r.Client.Status().Update(ctx, bkapp); err != nil {
		log.Error(err, "Unable to update app status.")
		return r.Result.withError(err)
	}
	return r.Result
}

// validate that there are no running hooks currently, return error if found any running hooks.
func (r *DeployActionReconciler) validateNoRunningHooks(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	// Check pre-release hook
	hook := resources.BuildPreReleaseHook(bkapp, bkapp.Status.FindHookStatus(paasv1alpha2.HookPreRelease))
	if hook != nil && hook.Progressing() {
		_, err := CheckAndUpdatePreReleaseHookStatus(ctx, r.Client, bkapp, resources.HookExecuteTimeoutThreshold)
		if err != nil {
			return err
		}
		return errors.WithStack(resources.ErrLastHookStillRunning)
	}
	return nil
}

// SetDefaultConditions set all conditions to initial value
func SetDefaultConditions(status *paasv1alpha2.AppStatus) {
	availableMessage := "rolling upgrade"
	availableStatus := metav1.ConditionUnknown
	latestAvailableCond := apimeta.FindStatusCondition(status.Conditions, paasv1alpha2.AppAvailable)
	if latestAvailableCond == nil {
		availableMessage = "First time deployment, service unavailable"
		availableStatus = metav1.ConditionFalse
	}

	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AppAvailable,
		Status:             availableStatus,
		Reason:             "NewDeploy",
		Message:            availableMessage,
		ObservedGeneration: status.ObservedGeneration,
	})
	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AppProgressing,
		Status:             metav1.ConditionTrue,
		Reason:             "NewDeploy",
		ObservedGeneration: status.ObservedGeneration,
	})
	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AddOnsProvisioned,
		Status:             metav1.ConditionUnknown,
		Reason:             "Initial",
		ObservedGeneration: status.ObservedGeneration,
	})
	apimeta.SetStatusCondition(&status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.HooksFinished,
		Status:             metav1.ConditionUnknown,
		Reason:             "Initial",
		ObservedGeneration: status.ObservedGeneration,
	})
}
