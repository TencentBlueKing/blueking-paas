/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

package autoscaling

import (
	"strconv"

	"github.com/samber/lo"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
	"bk.tencent.com/paas-app-operator/pkg/health"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

// GetWantedGPAs 根据应用生成对应的 GPA(general-pod-autoscaler) 配置列表
func GetWantedGPAs(app *paasv1alpha2.BkApp) []*autoscaling.GeneralPodAutoscaler {
	gpaList := []*autoscaling.GeneralPodAutoscaler{}
	specGetter := envs.NewAutoscalingSpecGetter(app)
	for _, proc := range app.Spec.Processes {
		// 若某个进程没有自动扩缩容配置，则跳过
		spec := specGetter.GetByProc(proc.Name)
		if spec == nil {
			continue
		}
		gpaList = append(gpaList, &autoscaling.GeneralPodAutoscaler{
			TypeMeta: metav1.TypeMeta{
				APIVersion: autoscaling.SchemeGroupVersion.String(),
				Kind:       "GeneralPodAutoscaler",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      names.GPA(app, proc.Name),
				Namespace: app.Namespace,
				Annotations: map[string]string{
					paasv1alpha2.ProcessNameKey:            proc.Name,
					paasv1alpha2.GPAComputeByLimitsAnnoKey: "true",
				},
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(app, schema.GroupVersionKind{
						Group:   paasv1alpha2.GroupVersion.Group,
						Version: paasv1alpha2.GroupVersion.Version,
						Kind:    paasv1alpha2.KindBkApp,
					}),
				},
			},
			Spec: autoscaling.GeneralPodAutoscalerSpec{
				AutoScalingDrivenMode: autoscaling.AutoScalingDrivenMode{
					MetricMode: &autoscaling.MetricMode{
						Metrics: buildMetricSpecs(spec),
					},
				},
				MinReplicas: &spec.MinReplicas,
				MaxReplicas: spec.MaxReplicas,
				ScaleTargetRef: autoscaling.CrossVersionObjectReference{
					APIVersion: "apps/v1",
					Kind:       "Deployment",
					Name:       names.Deployment(app, proc.Name),
				},
			},
		})
	}
	return gpaList
}

func buildMetricSpecs(spec *paasv1alpha2.AutoscalingSpec) []autoscaling.MetricSpec {
	if len(spec.Metrics) > 0 {
		return lo.Map(spec.Metrics, func(m paasv1alpha2.MetricSpec, _ int) autoscaling.MetricSpec {
			v, err := strconv.Atoi(m.Value)
			if err != nil {
				v = 85
			}
			return autoscaling.MetricSpec{
				Type: autoscaling.ResourceMetricSourceType,
				Resource: &autoscaling.ResourceMetricSource{
					Name: v1.ResourceCPU,
					Target: autoscaling.MetricTarget{
						Type:               autoscaling.UtilizationMetricType,
						AverageUtilization: lo.ToPtr(int32(v)),
					},
				},
			}
		})
	}
	// 无自定义 metrics，回退到默认
	switch spec.Policy {
	case paasv1alpha2.ScalingPolicyDefault:
		return []autoscaling.MetricSpec{{
			Type: autoscaling.ResourceMetricSourceType,
			Resource: &autoscaling.ResourceMetricSource{
				Name: v1.ResourceCPU,
				Target: autoscaling.MetricTarget{
					Type:               autoscaling.UtilizationMetricType,
					AverageUtilization: lo.ToPtr(int32(85)),
				},
			},
		}}
	}
	return nil
}

// GenGPAHealthStatus check if the GPA is healthy
// For a deployment:
//
//	healthy means the GPA is available, ready to scale workloads with policy.
//	unhealthy means the GPA is failed when reconciled.
func GenGPAHealthStatus(gpa *autoscaling.GeneralPodAutoscaler) *health.HealthStatus {
	for _, condition := range gpa.Status.Conditions {
		if condition.Status == v1.ConditionFalse {
			return &health.HealthStatus{
				Phase:   paasv1alpha2.HealthUnhealthy,
				Reason:  condition.Reason,
				Message: condition.Message,
			}
		}
	}

	return &health.HealthStatus{
		Phase:   paasv1alpha2.HealthHealthy,
		Reason:  paasv1alpha2.AutoscalingAvailable,
		Message: "",
	}
}
