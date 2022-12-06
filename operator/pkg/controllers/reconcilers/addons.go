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
	"errors"
	"fmt"

	"github.com/getsentry/sentry-go"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"

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
	client.Client
	Result         Result
	ExternalClient *external.Client
}

// Reconcile ...
func (r *AddonReconciler) Reconcile(ctx context.Context, bkapp *v1alpha1.BkApp) Result {
	err := r.doReconcile(ctx, bkapp)
	if err != nil {
		bkapp.Status.Phase = v1alpha1.AppFailed
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.AddOnsProvisioned,
			Status:             metav1.ConditionFalse,
			Reason:             errors.Unwrap(err).Error(),
			Message:            err.Error(),
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	} else {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               v1alpha1.AddOnsProvisioned,
			Status:             metav1.ConditionTrue,
			Reason:             "Provisioned",
			ObservedGeneration: bkapp.Status.ObservedGeneration,
		})
	}

	if updateErr := r.Status().Update(ctx, bkapp); updateErr != nil {
		sentry.CaptureException(updateErr)
		return r.Result.withError(updateErr)
	}
	return r.Result.withError(err)
}

func (r *AddonReconciler) doReconcile(ctx context.Context, bkapp *v1alpha1.BkApp) (err error) {
	log := logf.FromContext(ctx)

	var addons []string
	var appInfo *applications.BluekingAppInfo

	appInfo, err = applications.GetBkAppInfo(bkapp)
	if err != nil {
		sentry.CaptureException(err)
		log.Error(err, "failed to get bkapp info, skip addons reconcile")
		return fmt.Errorf("InvalidAnnotations: missing bkapp info, Detail: %w", err)
	}

	if addons, err = bkapp.ExtractAddons(); err != nil {
		sentry.CaptureException(err)
		log.Error(err, "failed to extract addons info from annotation, skip addons reconcile")
		return fmt.Errorf("InvalidAnnotations: invalid value for '%s', Detail: %w", v1alpha1.AddonsAnnoKey, err)
	}

	for _, addon := range addons {
		ctx, cancel := context.WithTimeout(ctx, external.DefaultTimeout)
		defer cancel()

		err = r.ExternalClient.ProvisionAddonInstance(
			ctx,
			appInfo.AppCode,
			appInfo.ModuleName,
			appInfo.Environment,
			addon,
		)
		if err != nil {
			sentry.CaptureException(err)
			log.Error(err, "failed to provision addon instance", "appInfo", appInfo, "addon", addon)
			return fmt.Errorf("ProvisionFailed: failed to provision '%s' instance, Detail: %w", addon, err)
		}
	}
	return nil
}
