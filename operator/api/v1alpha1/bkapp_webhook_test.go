/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
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
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
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
		web := bkapp.Spec.GetWebProcess()

		Expect(web.TargetPort).To(Equal(int32(5000)))
		Expect(web.CPU).To(Equal("4"))
		Expect(web.Memory).To(Equal("1Gi"))
		Expect(web.ImagePullPolicy).To(Equal(corev1.PullIfNotPresent))
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
						Image:      "nginx:latest",
						Replicas:   ReplicasTwo,
						TargetPort: 80,
						CPU:        "100m",
						Memory:     "100Mi",
					},
					{
						Name:     "hi",
						Image:    "busybox:latest",
						Replicas: ReplicasTwo,
						Command:  []string{"/bin/sh"},
						Args:     []string{"-c", "echo hi"},
						CPU:      "50m",
						Memory:   "50Mi",
					},
				},
			},
		}
	})

	Context("Test update BkApp actions", func() {
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

	Context("Test process other", func() {
		It("replicas too big", func() {
			newReplicas := int32(6)
			bkapp.Spec.Processes[0].Replicas = &newReplicas
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("at most support 5 replicas"))
		})

		It("Invalid quota", func() {
			bkapp.Spec.Processes[0].CPU = "5"
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("exceed limit"))

			bkapp.Spec.Processes[0].CPU = ""
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("quota required"))

			bkapp.Spec.Processes[0].CPU = "1C"
			err = bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("unsupported"))
		})
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
		It("Invalid envName", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "invalid-env", Process: "web", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("Invalid process name", func() {
			bkapp.Spec.EnvOverlay.Replicas = []ReplicasOverlay{
				{EnvName: "stag", Process: "invalid-proc", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
	})
})

var _ = Describe("Integrated tests for webhooks", func() {
	It("Create BkApp with minimal required fields", func() {
		bkapp := &BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: KindBkApp, APIVersion: GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-sample", Namespace: "default"},
			// Only include minimal required fields
			Spec: AppSpec{
				Processes: []Process{{Name: "web", Replicas: ReplicasOne, Image: "nginx:latest"}},
			},
		}
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		// Check if default values have been set
		var createdBkApp BkApp
		Expect(k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &createdBkApp)).NotTo(HaveOccurred())
		Expect(createdBkApp.Spec.Processes[0].TargetPort).To(Equal(ProcDefaultTargetPort))
	})
})
