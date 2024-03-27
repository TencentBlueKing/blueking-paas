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

package processes

import (
	"context"
	"encoding/json"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers/base"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
	"bk.tencent.com/paas-app-operator/pkg/metrics"
)

// NewServiceReconciler will return a ServiceReconciler with given k8s client
func NewServiceReconciler(client client.Client) *ServiceReconciler {
	return &ServiceReconciler{Client: client}
}

// ServiceReconciler 负责处理 Service 相关的调和逻辑
type ServiceReconciler struct {
	Client client.Client
	Result base.Result
}

// Reconcile ...
func (r *ServiceReconciler) Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) base.Result {
	current, err := r.listCurrentServices(ctx, bkapp)
	if err != nil {
		return r.Result.WithError(err)
	}

	expected := r.getWantedService(bkapp)
	outdated := kubeutil.FindExtraByName(current, expected)

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
		svc := BuildService(bkapp, &process)
		result = append(result, svc)
	}
	return result
}

// applyService 将 Service 应用到集群
func (r *ServiceReconciler) applyService(ctx context.Context, svc *corev1.Service) error {
	return kubeutil.UpsertObject(ctx, r.Client, svc, r.handleUpdate)
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

// BuildService 构建与指定进程关联的 Service 资源对象
func BuildService(bkapp *paasv1alpha2.BkApp, process *paasv1alpha2.Process) *corev1.Service {
	if process == nil {
		return nil
	}

	name := names.Service(bkapp, process.Name)
	svcLabels := labels.Deployment(bkapp, process.Name)
	selector := labels.PodSelector(bkapp, process.Name)

	return &corev1.Service{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "v1",
			Kind:       "Service",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:        name,
			Namespace:   bkapp.Namespace,
			Labels:      svcLabels,
			Annotations: map[string]string{},
		},
		Spec: corev1.ServiceSpec{
			Ports: []corev1.ServicePort{
				{
					Name:       "http",
					Port:       80,
					TargetPort: intstr.FromInt(int(process.TargetPort)),
					Protocol:   corev1.ProtocolTCP,
				},
			},
			Selector: selector,
		},
	}
}
