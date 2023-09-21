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

package v1alpha1

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"sigs.k8s.io/controller-runtime/pkg/conversion"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var _ = Describe("test conversion back and forth", func() {
	It("v1alpha1 -> hub -> v1alpha1", func() {
		v1alpha1bkapp := &BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       KindBkApp,
				APIVersion: GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{AddonsAnnoKey: `["add-on1"]`},
			},
			Spec: AppSpec{
				Processes: []Process{
					{
						Name:     "web",
						Image:    "nginx:latest",
						Replicas: ReplicasTwo,
						CPU:      "500m",
						Memory:   "256Mi",
					},
					{
						Name:     "worker",
						Replicas: ReplicasOne,
						Image:    "worker:latest",
						Autoscaling: &AutoscalingSpec{
							MinReplicas: 2,
							MaxReplicas: 5,
							Policy:      ScalingPolicyDefault,
						},
					},
				},
				Configuration: AppConfig{
					Env: []AppEnvVar{
						{Name: "ENV_NAME_1", Value: "env_value_1"},
						{Name: "ENV_NAME_2", Value: "env_value_2"},
					},
				},
				EnvOverlay: &AppEnvOverlay{
					Replicas: []ReplicasOverlay{
						{EnvName: "stag", Process: "web", Count: 10},
					},
					ResQuotas: []ResQuotaOverlay{
						{
							EnvName: "stag",
							Process: "web",
							Plan:    paasv1alpha2.ResQuotaPlan2C1G,
						},
					},
					EnvVariables: []EnvVarOverlay{
						{EnvName: "stag", Name: "ENV_NAME_1", Value: "env_value_3"},
					},
					Autoscaling: []AutoscalingOverlay{
						{
							EnvName: "stag",
							Process: "web",
							Spec: AutoscalingSpec{
								MinReplicas: 1,
								MaxReplicas: 3,
								Policy:      ScalingPolicyDefault,
							},
						},
					},
				},
			},
			Status: AppStatus{
				Phase: AppRunning,
				Conditions: []metav1.Condition{
					{
						LastTransitionTime: metav1.Now(),
						Message:            "",
						ObservedGeneration: 1,
						Reason:             AppAvailable,
						Status:             metav1.ConditionTrue,
						Type:               AppAvailable,
					},
				},
				Addresses: []Addressable{
					{
						SourceType: SourceTypeCustom,
						URL:        "https://example.com",
					},
				},
				Revision: &Revision{
					Revision: 1,
				},
				DeployId:           "1",
				ObservedGeneration: 2,
			},
		}

		// Convert the resource back and forth
		var v1alpha2bkapp paasv1alpha2.BkApp
		_ = v1alpha1bkapp.ConvertTo(conversion.Hub(&v1alpha2bkapp))
		var v1alpha1bkappFromConverted BkApp
		_ = v1alpha1bkappFromConverted.ConvertFrom(conversion.Hub(&v1alpha2bkapp))

		// Make sure the conversion is lossless.
		Expect(v1alpha1bkapp.Status).To(Equal(v1alpha1bkappFromConverted.Status))
		Expect(
			v1alpha1bkapp.Annotations[AddonsAnnoKey],
		).To(Equal(v1alpha1bkappFromConverted.Annotations[AddonsAnnoKey]))
		// 信息不丢失的情况下，转回 v1alpha1 后 Spec 会增加 Addons
		v1alpha1bkapp.Spec.Addons = []paasv1alpha2.Addon{{Name: "add-on1"}}
		Expect(v1alpha1bkapp.Spec).To(Equal(v1alpha1bkappFromConverted.Spec))
	})

	It("hub -> v1alpha1 -> hub", func() {
		v1alpha2bkapp := paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx: latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
					},
					{
						Name:         "worker",
						Replicas:     ReplicasOne,
						Command:      []string{"celery", "start"},
						ResQuotaPlan: "2x",
						Autoscaling: &paasv1alpha2.AutoscalingSpec{
							MinReplicas: 1,
							MaxReplicas: 10,
							Policy:      paasv1alpha2.ScalingPolicyDefault,
						},
					},
				},
				Addons: []paasv1alpha2.Addon{
					{Name: "addon-2", Specs: []paasv1alpha2.AddonSpec{{Name: "version", Value: "5.0"}}},
				},
				EnvOverlay: &paasv1alpha2.AppEnvOverlay{
					Replicas: []paasv1alpha2.ReplicasOverlay{
						{EnvName: "stag", Process: "web", Count: 10},
					},
					ResQuotas: []paasv1alpha2.ResQuotaOverlay{
						{
							EnvName: "stag",
							Process: "web",
							Plan:    paasv1alpha2.ResQuotaPlan2C1G,
						},
					},
					EnvVariables: []paasv1alpha2.EnvVarOverlay{
						{EnvName: "stag", Name: "ENV_NAME_1", Value: "env_value_3"},
					},
					Autoscaling: []paasv1alpha2.AutoscalingOverlay{
						{
							EnvName: "stag",
							Process: "web",
							Spec: paasv1alpha2.AutoscalingSpec{
								MinReplicas: 1,
								MaxReplicas: 3,
								Policy:      paasv1alpha2.ScalingPolicyDefault,
							},
						},
					},
				},
			},
			Status: paasv1alpha2.AppStatus{
				Phase: paasv1alpha2.AppRunning,
				Conditions: []metav1.Condition{
					{
						LastTransitionTime: metav1.Now(),
						Message:            "",
						ObservedGeneration: 1,
						Reason:             AppAvailable,
						Status:             metav1.ConditionTrue,
						Type:               AppAvailable,
					},
				},
				Addresses: []paasv1alpha2.Addressable{
					{
						SourceType: SourceTypeCustom,
						URL:        "https://example.com",
					},
				},
				Revision: &paasv1alpha2.Revision{
					Revision: 1,
				},
				DeployId:           "1",
				ObservedGeneration: 2,
				AddonStatuses: []paasv1alpha2.AddonStatus{
					{
						Name:  "addon-2",
						State: paasv1alpha2.AddonProvisioned,
						Specs: []paasv1alpha2.AddonSpec{{Name: "version", Value: "5.0"}},
					},
				},
			},
		}

		// Convert the resource back and forth
		var v1alpha1bkapp BkApp
		_ = v1alpha1bkapp.ConvertFrom(conversion.Hub(&v1alpha2bkapp))
		var v1alpha2bkappFromConverted paasv1alpha2.BkApp
		_ = v1alpha1bkapp.ConvertTo(conversion.Hub(&v1alpha2bkappFromConverted))

		// Make sure the conversion is lossless.
		Expect(v1alpha2bkapp.Spec).To(Equal(v1alpha2bkappFromConverted.Spec))
		Expect(v1alpha2bkapp.Status).To(Equal(v1alpha2bkappFromConverted.Status))
	})
})
