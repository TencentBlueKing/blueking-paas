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

	"github.com/pkg/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
)

// NewAddonReconciler will return a AddonReconciler with given k8s client and default bkpaas client
func NewAddonReconciler(client client.Client) *AddonReconciler {
	externalClient, err := external.GetDefaultClient()
	if err != nil {
		return nil
	}
	return &AddonReconciler{
		Client:         client,
		ExternalClient: externalClient,
	}
}

// AddonReconciler 负责处理分配增强服务实例
type AddonReconciler struct {
	Client         client.Client
	Result         Result
	ExternalClient *external.Client
}

// Reconcile ...
func (r *AddonReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result {
	// 未启用增强服务, 直接返回
	if bkapp.Spec.Addons == nil {
		return r.Result.withError(nil)
	}

	addonStatuses, err := r.doReconcile(ctx, bkapp)
	if err != nil {
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AddOnsProvisioned,
			Status:             metav1.ConditionFalse,
			Reason:             "InternalServerError",
			Message:            err.Error(),
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	} else {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AddOnsProvisioned,
			Status:             metav1.ConditionTrue,
			Reason:             "Provisioned",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	}

	bkapp.Status.AddonStatuses = addonStatuses

	if updateErr := r.Client.Status().Update(ctx, bkapp); updateErr != nil {
		return r.Result.withError(updateErr)
	}
	return r.Result.withError(err)
}

func (r *AddonReconciler) doReconcile(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) ([]paasv1alpha2.AddonStatus, error) {
	log := logf.FromContext(ctx)

	var appInfo *applications.BluekingAppInfo

	appInfo, err := applications.GetBkAppInfo(bkapp)
	if err != nil {
		log.Error(err, "failed to get bkapp info, skip addons reconcile")
		return nil, errors.Wrap(err, "InvalidAnnotations: missing bkapp info, detail")
	}

	statuses := make([]paasv1alpha2.AddonStatus, 0)
	addons := bkapp.Spec.Addons
	for _, addon := range addons {
		status, err := r.provisionAddon(ctx, appInfo, addon)
		if err != nil {
			log.Error(err, "failed to provision addon instance", "appInfo", appInfo, "addon", addon.Name)
			return statuses, err
		}
		statuses = append(statuses, *status)
	}

	return statuses, nil
}

func (r *AddonReconciler) provisionAddon(
	ctx context.Context,
	appInfo *applications.BluekingAppInfo,
	addon paasv1alpha2.Addon,
) (*paasv1alpha2.AddonStatus, error) {
	var reqSpecs *external.AddonSpecs
	if addon.Specs != nil {
		specsMap := make(map[string]string)
		for _, spec := range addon.Specs {
			specsMap[spec.Name] = spec.Value
		}
		reqSpecs = &external.AddonSpecs{
			Specs: specsMap,
		}
	}

	timeoutCtx, pCancel := context.WithTimeout(ctx, external.DefaultTimeout)
	defer pCancel()

	svcID, err := r.ExternalClient.ProvisionAddonInstance(
		timeoutCtx,
		appInfo.AppCode,
		appInfo.ModuleName,
		appInfo.Environment,
		addon.Name,
		reqSpecs,
	)
	if err != nil {
		return &paasv1alpha2.AddonStatus{
			Name:    addon.Name,
			State:   paasv1alpha2.AddonFailed,
			Message: fmt.Sprintf("Provision failed: %s", err),
		}, errors.Wrapf(err, "Addon '%s' provision failed, detail", addon.Name)
	}

	addOnStatus := &paasv1alpha2.AddonStatus{
		Name:  addon.Name,
		State: paasv1alpha2.AddonProvisioned,
	}

	timeoutCtx, gCancel := context.WithTimeout(ctx, external.DefaultTimeout)
	defer gCancel()
	// 将增强服务 Specs 添加到 .status.addonStatuses.specs
	specResult, err := r.ExternalClient.QueryAddonSpecs(timeoutCtx, appInfo.AppCode, appInfo.ModuleName, svcID)
	if err != nil {
		for _, status := range specResult.Data {
			addOnStatus.Specs = append(
				addOnStatus.Specs,
				paasv1alpha2.AddonSpec{Name: status.Name, Value: status.Value},
			)
		}
	}

	return addOnStatus, nil
}
