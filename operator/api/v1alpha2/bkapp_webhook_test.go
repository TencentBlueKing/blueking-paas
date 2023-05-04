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

package v1alpha2_test

import (
	"fmt"
	"math"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/utils/stringx"
)

var _ = Describe("test webhook.Defaulter", func() {
	It("normal case", func() {
		bkapp := &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{
				Processes: []paasv1alpha2.Process{
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
	var bkapp *paasv1alpha2.BkApp

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
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
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:       "web",
						Replicas:   paasv1alpha2.ReplicasTwo,
						TargetPort: 80,
					},
					{
						Name:     "hi",
						Replicas: paasv1alpha2.ReplicasTwo,
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
			bkapp.Spec.Processes = []paasv1alpha2.Process{}
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

		It("replicas is too big", func() {
			var newReplicas int32 = math.MaxUint16
			bkapp.Spec.Processes[0].Replicas = &newReplicas
			err := bkapp.ValidateCreate()
			Expect(
				err.Error(),
			).To(ContainSubstring(fmt.Sprintf("at most support %d replicas", config.Global.GetProcMaxReplicas())))
		})
	})

	Context("Test process autoscaling", func() {
		It("Invalid minReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: true, MinReplicas: 0, MaxReplicas: 5, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("minReplicas must be greater than 0"))
		})

		It("Invalid maxReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: true, MinReplicas: 1, MaxReplicas: 6, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("at most support 5 replicas"))
		})

		It("maxReplicas < minReplicas", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: true, MinReplicas: 3, MaxReplicas: 2, Policy: paasv1alpha2.ScalingPolicyDefault,
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("maxReplicas must be greater than or equal to minReplicas"))
		})

		It("policy required", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: true, MinReplicas: 1, MaxReplicas: 3, Policy: "",
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("autoscaling policy is required"))
		})

		It("policy must supported", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: true, MinReplicas: 1, MaxReplicas: 3, Policy: "fake",
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\""))
		})

		It("disable autoscaling cause skip validate", func() {
			bkapp.Spec.Processes[0].Autoscaling = &paasv1alpha2.AutoscalingSpec{
				Enabled: false, MinReplicas: 3, MaxReplicas: 2, Policy: "fake",
			}
			Expect(bkapp.ValidateCreate()).To(BeNil())
		})
	})

	Context("Test envOverlay", func() {
		BeforeEach(func() {
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{}
		})
		It("Normal", func() {
			bkapp.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{
				Replicas: []paasv1alpha2.ReplicasOverlay{
					{EnvName: "stag", Process: "web", Count: 1},
				},
				EnvVariables: []paasv1alpha2.EnvVarOverlay{
					{EnvName: "stag", Name: "foo", Value: "foo-value"},
				},
				Autoscaling: []paasv1alpha2.AutoscalingOverlay{
					{EnvName: "stag", Process: "web", Policy: paasv1alpha2.ScalingPolicyDefault},
				},
			}

			err := bkapp.ValidateCreate()
			Expect(err).To(BeNil())
		})
		It("[replicas] invalid envName", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "invalid-env", Process: "web", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[replicas] invalid process name", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "stag", Process: "invalid-proc", Count: 1},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[replicas] invalid count", func() {
			bkapp.Spec.EnvOverlay.Replicas = []paasv1alpha2.ReplicasOverlay{
				{EnvName: "stag", Process: "web", Count: 100},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("count can't be greater than "))
		})
		It("[envVariables] invalid envName", func() {
			bkapp.Spec.EnvOverlay.EnvVariables = []paasv1alpha2.EnvVarOverlay{
				{EnvName: "invalid-env", Name: "foo", Value: "bar"},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[autoscaling] invalid envName", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{EnvName: "invalid-env", Process: "web", Policy: paasv1alpha2.ScalingPolicyDefault},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("envName is invalid"))
		})
		It("[autoscaling] invalid process name", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{EnvName: "stag", Process: "invalid-proc", Policy: paasv1alpha2.ScalingPolicyDefault},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("process name is invalid"))
		})
		It("[autoscaling] invalid policy", func() {
			bkapp.Spec.EnvOverlay.Autoscaling = []paasv1alpha2.AutoscalingOverlay{
				{EnvName: "stag", Process: "web", Policy: "fake"},
			}
			err := bkapp.ValidateCreate()
			Expect(err.Error()).To(ContainSubstring("supported values: \"default\""))
		})
	})
})

var _ = Describe("Integrated tests for webhooks, v1alpha1 version", func() {
	var suffix string

	// A shortcut to build a v1alpha1/BkApp object
	buildApp := func(spec paasv1alpha1.AppSpec) *paasv1alpha1.BkApp {
		ret := &paasv1alpha1.BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: paasv1alpha1.KindBkApp, APIVersion: paasv1alpha1.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-" + suffix, Namespace: "default"},
		}
		ret.Spec = spec
		return ret
	}

	BeforeEach(func() {
		suffix = strings.ToLower(stringx.RandLetters(6))
	})

	It("Create BkApp with minimal required fields", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest"},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
	})

	It("Check default values was set", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne, Image: "nginx:latest"},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())

		// Check if default values have been set
		var createdBkApp paasv1alpha2.BkApp
		Expect(k8sClient.Get(ctx, client.ObjectKeyFromObject(bkapp), &createdBkApp)).NotTo(HaveOccurred())
		Expect(createdBkApp.Spec.Processes[0].TargetPort).To(Equal(paasv1alpha2.ProcDefaultTargetPort))
	})

	It("Create BkApp with duplicated processes", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})

	It("Create BkApp with image absent", func() {
		bkapp := buildApp(paasv1alpha1.AppSpec{
			Processes: []paasv1alpha1.Process{
				{Name: "web", Replicas: paasv1alpha1.ReplicasOne},
			},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})
})

var _ = Describe("Integrated tests for webhooks, v1alpha2 version", func() {
	var suffix string

	// A shortcut to build a v1alpha2/BkApp object
	buildApp := func(spec paasv1alpha2.AppSpec) *paasv1alpha2.BkApp {
		ret := &paasv1alpha2.BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: paasv1alpha2.KindBkApp, APIVersion: paasv1alpha2.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "bkapp-" + suffix, Namespace: "default"},
		}
		ret.Spec = spec
		return ret
	}

	BeforeEach(func() {
		suffix = strings.ToLower(stringx.RandLetters(6))
	})

	It("Create BkApp with minimal required fields", func() {
		bkapp := buildApp(paasv1alpha2.AppSpec{
			Build:     paasv1alpha2.BuildConfig{Image: "nginx:latest"},
			Processes: []paasv1alpha2.Process{{Name: "web", Replicas: paasv1alpha2.ReplicasOne}},
		})
		Expect(k8sClient.Create(ctx, bkapp)).NotTo(HaveOccurred())
	})

	It("Create BkApp with image missing", func() {
		bkapp := buildApp(paasv1alpha2.AppSpec{
			Processes: []paasv1alpha2.Process{{Name: "web", Replicas: paasv1alpha2.ReplicasOne}},
		})
		Expect(k8sClient.Create(ctx, bkapp)).To(HaveOccurred())
	})
})
