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

// Package autoscaling provides autoscaling reconciler
package autoscaling

import (
	"context"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
	"bk.tencent.com/paas-app-operator/pkg/metrics"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

// NewReconciler will return a Reconciler with given k8s client
func NewReconciler(client client.Client) *Reconciler {
	if !config.Global.IsAutoscalingEnabled() {
		return nil
	}
	return &Reconciler{Client: client}
}

// Reconciler 负责处理 Deployment 相关的调和逻辑
type Reconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile ...
func (r *Reconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	current, err := r.getCurrentState(ctx, bkapp)
	if err != nil {
		return r.Result.WithError(err)
	}
	expected := GetWantedGPAs(bkapp)
	outdated := kubeutil.FindExtraByName(current, expected)

	if len(outdated) != 0 {
		for _, gpa := range outdated {
			if err = r.Client.Delete(ctx, gpa); err != nil {
				metrics.IncDeleteOutdatedGpaFailures(bkapp, gpa.Name)
				return r.Result.WithError(err)
			}
		}
	}
	for _, gpa := range expected {
		if err = r.deploy(ctx, gpa); err != nil {
			metrics.IncDeployExpectedGpaFailures(bkapp, gpa.Name)
			return r.Result.WithError(err)
		}
	}

	if err = r.updateCondition(ctx, bkapp); err != nil {
		metrics.IncAutoscaleUpdateBkappStatusFailures(bkapp)
		return r.Result.WithError(err)
	}
	return r.Result
}

// 获取应用当前在集群中的状态
func (r *Reconciler) getCurrentState(
	ctx context.Context, bkapp *paasv1alpha2.BkApp,
) (result []*autoscaling.GeneralPodAutoscaler, err error) {
	gpaList := autoscaling.GeneralPodAutoscalerList{}
	err = r.Client.List(
		ctx, &gpaList, client.InNamespace(bkapp.Namespace),
		client.MatchingFields{paasv1alpha2.KubeResOwnerKey: bkapp.Name},
	)
	if err != nil {
		return nil, errors.Wrap(err, "failed to list app's GPA")
	}

	return lo.ToSlicePtr(gpaList.Items), nil
}

// 将给定的 general-pod-autoscaler 下发到 k8s 集群中, 如果不存在则创建，若存在，则更新，不会进行版本比较
func (r *Reconciler) deploy(ctx context.Context, gpa *autoscaling.GeneralPodAutoscaler) error {
	return kubeutil.UpsertObject(ctx, r.Client, gpa, r.updateHandler)
}

// GPA 更新策略: 总是更新，但是需要填充 resourceVersion，uid 等信息，否则无法通过 gpa webhook 的检查
func (r *Reconciler) updateHandler(
	ctx context.Context,
	cli client.Client,
	current *autoscaling.GeneralPodAutoscaler,
	want *autoscaling.GeneralPodAutoscaler,
) error {
	want.UID = current.UID
	want.Generation = current.Generation
	want.ResourceVersion = current.ResourceVersion
	want.CreationTimestamp = current.CreationTimestamp

	if err := cli.Update(ctx, want); err != nil {
		return errors.Wrapf(err, "update GPA(%s)", want.GetName())
	}
	return nil
}

// 根据 GPA 状态（Conditions），更新 BkApp 状态（Conditions）
func (r *Reconciler) updateCondition(ctx context.Context, bkapp *paasv1alpha2.BkApp) error {
	current, err := r.getCurrentState(ctx, bkapp)
	if err != nil {
		return err
	}

	if len(current) == 0 {
		apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
			Type:               paasv1alpha2.AutoscalingAvailable,
			Status:             metav1.ConditionUnknown,
			Reason:             "Disabled",
			Message:            "Process autoscaling feature not turned on",
			ObservedGeneration: bkapp.Generation,
		})
		return nil
	}

	for _, gpa := range current {
		healthStatus := GenGPAHealthStatus(gpa)
		if healthStatus.Phase != paasv1alpha2.HealthHealthy {
			apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
				Type:               paasv1alpha2.AutoscalingAvailable,
				Status:             metav1.ConditionFalse,
				Reason:             "AutoscalerFailure",
				Message:            gpa.Name + ": " + healthStatus.Message,
				ObservedGeneration: bkapp.Generation,
			})
			return nil
		}
	}

	apimeta.SetStatusCondition(&bkapp.Status.Conditions, metav1.Condition{
		Type:               paasv1alpha2.AutoscalingAvailable,
		Status:             metav1.ConditionTrue,
		Reason:             "AutoscalingAvailable",
		ObservedGeneration: bkapp.Generation,
	})
	return nil
}
