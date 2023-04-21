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

package v1alpha2

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var _ = Describe("test webhook.Defaulter", func() {
	It("normal case", func() {
		bkapp := &BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       KindBkApp,
				APIVersion: GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: AppSpec{
				Processes: []Process{
					{
						Name: "web",
					},
				},
			},
		}

		bkapp.Default()
		Expect(bkapp.Spec.Build.ImagePullPolicy).To(Equal(corev1.PullIfNotPresent))

		web := bkapp.Spec.GetWebProcess()
		Expect(web.TargetPort).To(Equal(int32(5000)))
		Expect(web.ResQuotaPlan).To(Equal("default"))
	})
})

var _ = Describe("test webhook.Validator", func() {
	var bkapp *BkApp

	BeforeEach(func() {
		bkapp = &BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       KindBkApp,
				APIVersion: GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: AppSpec{
				Processes: []Process{
					{
						Name:       "web",
						Replicas:   ReplicasTwo,
						TargetPort: 80,
					},
					{
						Name:     "hi",
						Replicas: ReplicasTwo,
						Command:  []string{"/bin/sh"},
						Args:     []string{"-c", "echo hi"},
					},
				},
			},
		}
	})

	Context("Test BkApp actions", func() {
		It("Create normal", func() {
			err := bkapp.ValidateCreate()
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Update normal", func() {
			err := bkapp.ValidateUpdate(bkapp)
			Expect(err).ShouldNot(HaveOccurred())
		})

		It("Delete normal", func() {
			err := bkapp.ValidateDelete()
			Expect(err).ShouldNot(HaveOccurred())
		})
	})

	Context("Test app's basic fields", func() {
		It("App name invalid", func() {
			bkapp.Name = "bkapp-sample-very-long-long"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))

			bkapp.Name = "bkapp-sample-UPPER-CASE"
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))
		})
	})

	Context("Test process basic", func() {
		It("Processes empty", func() {
			bkapp.Spec.Processes = []Process{}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("processes can't be empty"))
		})

		It("Process name duplicated", func() {
			bkapp.Spec.Processes[1].Name = "web"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring(`process "web" is duplicated`))
		})

		It("web process missing", func() {
			bkapp.Spec.Processes[0].Name = "hello"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring(`"web" process is required`))
		})

		It("process name invalid", func() {
			bkapp.Spec.Processes[1].Name = "Web"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))

			bkapp.Spec.Processes[1].Name = "web-hello-hi-too-long"
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("must match regex"))
		})
	})

	// TODO: Add tests for Build field

	Context("Test process other", func() {
		// TODO: Fix this test case
		/*
			It("replicas too big", func() {
				newReplicas := int32(6)
				bkapp.Spec.Processes[0].Replicas = &newReplicas
				err := bkapp.ValidateCreate()
				Expect(err.Error()).To(ContainSubstring("at most support 5 replicas"))
			})
		*/

		// TODO: Add tests for ResQuotaPlan
	})

	Context("Test envOverlay", func() {
		BeforeEach(func() {
			bkapp.Spec.EnvOverlay = &AppEnvOverlay{}
		})
		It("Normal", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "stag", Process: "web", Count: 1},
			}
			bkapp.Spec.EnvOverlay.EnvVariables = []EnvVarOverlay{
				{EnvName: "stag", Name: "foo", Value: "foo-value"},
			}

			err := bkapp.ValidateCreate()
			Expect(err).ShouldNot(HaveOccurred())
		})
		It("[replicas] invalid envName", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "invalid-env", Process: "web", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[replicas] invalid process name", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "stag", Process: "invalid-proc", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[replicas] invalid count", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "stag", Process: "web", Count: 100},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("count can't be greater than "))
		})
	})
})

// TODO: Fix this integrated test, currently it will fail because we are unable to make
// webhooks in two API versions running.
/*
var _ = Describe("Integrated tests for webhooks", func() {
	It("Create BkApp with minimal required fields", func() {
		bkapp := &BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: KindBkApp, APIVersion: GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-sample", Namespace: "default"},
			// Only include minimal required fields
			Spec: AppSpec{
				Processes: []Process{{Name: "web", Replicas: ReplicasOne}},
			},
		}
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		// Check if default values have been set
		var createdBkApp BkApp
		Expect(k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &createdBkApp)).NotTo(HaveOccurred())
		Expect(createdBkApp.Spec.Processes[0].TargetPort).To(Equal(ProcDefaultTargetPort))
	})
})
*/
