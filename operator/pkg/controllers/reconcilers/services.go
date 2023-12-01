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
	"encoding/json"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// NewServiceReconciler will return a ServiceReconciler with given k8s client
func NewServiceReconciler(client client.Client) *ServiceReconciler {
	return &ServiceReconciler{Client: client}
}

// ServiceReconciler 负责处理 Service 相关的调和逻辑
type ServiceReconciler struct {
	Client client.Client
	Result Result
}

// Reconcile ...
func (r *ServiceReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result {
	current, err := r.listCurrentServices(ctx, bkapp)
	if err != nil {
		return r.Result.WithError(err)
	}

	expected := r.getWantedService(bkapp)
	outdated := FindExtraByName(current, expected)

	if len(outdated) != 0 {
		for _, svc := range outdated {
			if err = r.Client.Delete(ctx, svc); err != nil {
				metrics.IncDeleteOutdatedServiceFailures(bkapp, svc.Name)
				return r.Result.WithError(err)
			}
		}
	}
	for _, svc := range expected {
		if err = r.applyService(ctx, svc); err != nil {
			metrics.IncDeployExpectedServiceFailures(bkapp, svc.Name)
			return r.Result.WithError(err)
		}
	}
	return r.Result
}

// 获取当前在集群中的与该应用关联的 Service
func (r *ServiceReconciler) listCurrentServices(
	ctx context.Context,
	bkapp *paasv1alpha2.BkApp,
) ([]*corev1.Service, error) {
	current := corev1.ServiceList{}

	if err := r.Client.List(
		ctx, &current,
		client.InNamespace(bkapp.GetNamespace()),
		client.MatchingLabels{paasv1alpha2.BkAppNameKey: bkapp.GetName()},
	); err != nil {
		return nil, errors.Wrap(err, "failed to list app's Service")
	}
	return lo.ToSlicePtr(current.Items), nil
}

// getWantedService 获取应用期望的 Service 列表
func (r *ServiceReconciler) getWantedService(bkapp *paasv1alpha2.BkApp) (result []*corev1.Service) {
	for _, process := range bkapp.Spec.Processes {
		svc := resources.BuildService(bkapp, &process)
		result = append(result, svc)
	}
	return result
}

// applyService 将 Service 应用到集群
func (r *ServiceReconciler) applyService(ctx context.Context, svc *corev1.Service) error {
	return UpsertObject(ctx, r.Client, svc, r.handleUpdate)
}

// Service 更新策略: Spec 不一致则更新
func (r *ServiceReconciler) handleUpdate(
	ctx context.Context,
	cli client.Client,
	current *corev1.Service,
	want *corev1.Service,
) error {
	if !equality.Semantic.DeepEqual(current.Spec.Ports, want.Spec.Ports) ||
		!equality.Semantic.DeepEqual(current.Spec.Selector, want.Spec.Selector) {
		patch, err := json.Marshal(want)
		if err != nil {
			return errors.Wrapf(
				err,
				"failed to patch update Service(%s/%s) while marshal patching data",
				want.GetNamespace(),
				want.GetName(),
			)
		}
		if err = cli.Patch(ctx, current, client.RawPatch(types.MergePatchType, patch)); err != nil {
			return errors.Wrapf(
				err,
				"failed to patch update Service(%s/%s)",
				want.GetNamespace(),
				want.GetName(),
			)
		}
	}
	return nil
}
