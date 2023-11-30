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
	"bk.tencent.com/paas-app-operator/pkg/metrics"
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
	// 未启用增强服务, 清空 addon 的历史 status 并返回
	if len(bkapp.Spec.Addons) == 0 {
		if bkapp.Status.AddonStatuses != nil {
			bkapp.Status.AddonStatuses = nil
		}
		return r.Result
	}

	addonStatuses, err := r.doReconcile(ctx, bkapp)
	if err != nil {
		bkapp.Status.Phase = paasv1alpha2.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AddOnsProvisioned,
			Status:             metav1.ConditionFalse,
			Reason:             "InternalServerError",
			Message:            err.Error(),
			ObservedGeneration: bkapp.Generation,
		})
	} else {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AddOnsProvisioned,
			Status:             metav1.ConditionTrue,
			Reason:             "Provisioned",
			ObservedGeneration: bkapp.Generation,
		})
	}

	bkapp.Status.AddonStatuses = addonStatuses

	// 增强服务分配失败, 直接终止 reconcile
	if err != nil {
		return r.Result.End()
	}
	return r.Result
}

func (r *AddonReconciler) doReconcile(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) ([]paasv1alpha2.AddonStatus, error) {
	log := logf.FromContext(ctx)

	var appInfo *applications.BluekingAppInfo

	appInfo, err := applications.GetBkAppInfo(bkapp)
	if err != nil {
		metrics.IncGetBkappInfoFailures(bkapp)
		log.Error(err, "failed to get bkapp info, skip addons reconcile")
		return nil, errors.Wrap(err, "InvalidAnnotations: missing bkapp info, detail")
	}

	statuses := make([]paasv1alpha2.AddonStatus, 0)
	for _, addon := range bkapp.Spec.Addons {
		status, err := r.provisionAddon(ctx, appInfo, addon)
		statuses = append(statuses, status)
		if err != nil {
			metrics.IncProvisionAddonInstanceFailures(bkapp)
			log.Error(err, "failed to provision addon instance", "appInfo", appInfo, "addon", addon.Name)
			return statuses, err
		}
	}

	return statuses, nil
}

func (r *AddonReconciler) provisionAddon(
	ctx context.Context,
	appInfo *applications.BluekingAppInfo,
	addon paasv1alpha2.Addon,
) (paasv1alpha2.AddonStatus, error) {
	specsMap := make(map[string]string)
	for _, spec := range addon.Specs {
		specsMap[spec.Name] = spec.Value
	}

	timeoutCtx, postCancel := context.WithTimeout(ctx, external.DefaultTimeout)
	defer postCancel()

	svcID, err := r.ExternalClient.ProvisionAddonInstance(
		timeoutCtx,
		appInfo.AppCode,
		appInfo.ModuleName,
		appInfo.Environment,
		addon.Name,
		external.AddonSpecs{Specs: specsMap},
	)
	if err != nil {
		return paasv1alpha2.AddonStatus{
			Name:    addon.Name,
			State:   paasv1alpha2.AddonFailed,
			Message: fmt.Sprintf("Provision failed: %s", err),
		}, errors.Wrapf(err, "Addon '%s' provision failed, detail", addon.Name)
	}

	addonStatus := paasv1alpha2.AddonStatus{
		Name:  addon.Name,
		State: paasv1alpha2.AddonProvisioned,
	}

	timeoutCtx, getCancel := context.WithTimeout(ctx, external.DefaultTimeout)
	defer getCancel()
	// 将增强服务 Specs 添加到 .status.addonStatuses.specs
	specResult, err := r.ExternalClient.QueryAddonSpecs(timeoutCtx, appInfo.AppCode, appInfo.ModuleName, svcID)
	if err != nil {
		metrics.IncQueryAddonSpecsFailures(appInfo.AppCode, appInfo.ModuleName, svcID)
		return addonStatus, errors.Wrapf(err, "QueryAddonSpecs failed, detail")
	}

	for name, value := range specResult.Data {
		addonStatus.Specs = append(addonStatus.Specs, paasv1alpha2.AddonSpec{Name: name, Value: value})
	}

	return addonStatus, nil
}
