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
	err := r.doReconcile(ctx, bkapp)
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

	if updateErr := r.Client.Status().Update(ctx, bkapp); updateErr != nil {
		return r.Result.withError(updateErr)
	}
	return r.Result.withError(err)
}

func (r *AddonReconciler) doReconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) (err error) {
	log := logf.FromContext(ctx)

	var addons []string
	var appInfo *applications.BluekingAppInfo

	appInfo, err = applications.GetBkAppInfo(bkapp)
	if err != nil {
		log.Error(err, "failed to get bkapp info, skip addons reconcile")
		return errors.Wrap(err, "InvalidAnnotations: missing bkapp info, Detail")
	}

	if addons, err = bkapp.ExtractAddons(); err != nil {
		log.Error(err, "failed to extract addons info from annotation, skip addons reconcile")
		return errors.Wrapf(err, "InvalidAnnotations: invalid value for '%s', Detail", paasv1alpha2.AddonsAnnoKey)
	}

	for _, addon := range addons {
		cancelCtx, cancel := context.WithTimeout(ctx, external.DefaultTimeout)
		defer cancel()

		err = r.ExternalClient.ProvisionAddonInstance(
			cancelCtx,
			appInfo.AppCode,
			appInfo.ModuleName,
			appInfo.Environment,
			addon,
		)
		if err != nil {
			log.Error(err, "failed to provision addon instance", "appInfo", appInfo, "addon", addon)
			return errors.Wrapf(err, "ProvisionFailed: failed to provision '%s' instance, Detail", addon)
		}
	}
	return nil
}
