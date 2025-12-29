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

package common_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common"
)

var _ = Describe("Test selector functions", func() {
	var bkapp *paasv1alpha2.BkApp

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasOne,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
				},
			},
		}
	})

	Describe("BuildNodeSelector", func() {
		It("should return nil when no nodeSelector is defined", func() {
			result := common.BuildNodeSelector(bkapp)
			Expect(result).To(BeNil())
		})

		It("should return user-defined nodeSelector", func() {
			bkapp.Spec.Schedule = &paasv1alpha2.Schedule{
				NodeSelector: map[string]string{
					"disktype": "ssd",
					"env":      "production",
				},
			}
			result := common.BuildNodeSelector(bkapp)
			Expect(result).To(Equal(map[string]string{
				"disktype": "ssd",
				"env":      "production",
			}))
		})

		It("should return egress nodeSelector from annotation", func() {
			bkapp.Annotations[paasv1alpha2.EgressClusterStateNameAnnoKey] = "eng-cstate-test"
			result := common.BuildNodeSelector(bkapp)
			Expect(result).To(Equal(map[string]string{"eng-cstate-test": "1"}))
		})

		It("should merge egress and user-defined nodeSelector", func() {
			bkapp.Annotations[paasv1alpha2.EgressClusterStateNameAnnoKey] = "eng-cstate-test"
			bkapp.Spec.Schedule = &paasv1alpha2.Schedule{
				NodeSelector: map[string]string{
					"disktype": "ssd",
				},
			}
			result := common.BuildNodeSelector(bkapp)
			Expect(result).To(Equal(map[string]string{
				"eng-cstate-test": "1",
				"disktype":        "ssd",
			}))
		})

		It("user-defined nodeSelector should take precedence over egress", func() {
			bkapp.Annotations[paasv1alpha2.EgressClusterStateNameAnnoKey] = "eng-cstate-test"
			bkapp.Spec.Schedule = &paasv1alpha2.Schedule{
				NodeSelector: map[string]string{
					"eng-cstate-test": "2", // Override egress value
				},
			}
			result := common.BuildNodeSelector(bkapp)
			Expect(result).To(Equal(map[string]string{
				"eng-cstate-test": "2",
			}))
		})
	})

	Describe("BuildTolerations", func() {
		It("should return nil when no tolerations are defined", func() {
			result := common.BuildTolerations(bkapp)
			Expect(result).To(BeNil())
		})

		It("should return user-defined tolerations", func() {
			bkapp.Spec.Schedule = &paasv1alpha2.Schedule{
				Tolerations: []corev1.Toleration{
					{
						Key:      "key1",
						Operator: corev1.TolerationOpEqual,
						Value:    "value1",
						Effect:   corev1.TaintEffectNoSchedule,
					},
					{
						Key:      "key2",
						Operator: corev1.TolerationOpExists,
						Effect:   corev1.TaintEffectNoExecute,
					},
				},
			}
			result := common.BuildTolerations(bkapp)
			Expect(result).To(HaveLen(2))
			Expect(result[0].Key).To(Equal("key1"))
			Expect(result[1].Key).To(Equal("key2"))
		})
	})
})
