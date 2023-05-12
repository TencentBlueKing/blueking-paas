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
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
)

var _ = Describe("test compat", func() {
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
					Image:           "nginx:latest",
					ImagePullPolicy: corev1.PullIfNotPresent,
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
					{
						Name:         "hi",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						Command:      []string{"/bin/sh"},
						Args:         []string{"-c", "echo hi"},
					},
				},
			},
		}
	})

	Context("Test ProcImageGetter", func() {
		It("Get Legacy", func() {
			_ = kubetypes.SetJsonAnnotation(
				bkapp, paasv1alpha2.LegacyProcImageAnnoKey, paasv1alpha2.LegacyProcConfig{
					"web": {"image": "busybox:1.0.0", "policy": "Never"},
				},
			)
			getter := paasv1alpha2.NewProcImageGetter(bkapp)

			// legacy has higher priority than standard configuration
			image, pullPolicy, _ := getter.Get("web")
			Expect(image).To(Equal("busybox:1.0.0"))
			Expect(pullPolicy).To(Equal(corev1.PullNever))

			image, pullPolicy, _ = getter.Get("hi")
			Expect(image).To(Equal("nginx:latest"))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))
		})

		It("Get Standard", func() {
			getter := paasv1alpha2.NewProcImageGetter(bkapp)

			image, pullPolicy, _ := getter.Get("web")
			Expect(image).To(Equal("nginx:latest"))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))

			image, pullPolicy, _ = getter.Get("hi")
			Expect(image).To(Equal("nginx:latest"))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))

			image, pullPolicy, _ = getter.Get("hello")
			Expect(image).To(Equal("nginx:latest"))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))
		})

		It("Get Nothing", func() {
			bkapp.Spec.Build.Image = ""
			getter := paasv1alpha2.NewProcImageGetter(bkapp)

			image, pullPolicy, err := getter.Get("web")
			Expect(image).To(Equal(""))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))
			Expect(err).NotTo(BeNil())

			image, _, err = getter.Get("hello")
			Expect(image).To(Equal(""))
			Expect(pullPolicy).To(Equal(corev1.PullIfNotPresent))
			Expect(err).NotTo(BeNil())
		})
	})

	Context("Test ProcResourcesGetter", func() {
		It("Get Default", func() {
			resReq := paasv1alpha2.NewProcResourcesGetter(bkapp).GetDefault()
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("250m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("512Mi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("1"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
		})

		It("Get Legacy", func() {
			_ = kubetypes.SetJsonAnnotation(
				bkapp, paasv1alpha2.LegacyProcResAnnoKey, paasv1alpha2.LegacyProcConfig{
					"web": {"cpu": "2", "memory": "2Gi"},
				},
			)
			getter := paasv1alpha2.NewProcResourcesGetter(bkapp)
			resReq, _ := getter.Get("web")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("500m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("2"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
		})

		It("Get Standard", func() {
			bkapp.Spec.Processes[1].ResQuotaPlan = paasv1alpha2.ResQuotaPlan4C2G
			getter := paasv1alpha2.NewProcResourcesGetter(bkapp)

			resReq, _ := getter.Get("web")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("250m"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("512Mi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("1"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())

			resReq, _ = getter.Get("hi")
			Expect(resReq.Requests.Cpu().Equal(resource.MustParse("1"))).To(BeTrue())
			Expect(resReq.Requests.Memory().Equal(resource.MustParse("1Gi"))).To(BeTrue())
			Expect(resReq.Limits.Cpu().Equal(resource.MustParse("4"))).To(BeTrue())
			Expect(resReq.Limits.Memory().Equal(resource.MustParse("2Gi"))).To(BeTrue())
		})

		It("Get Nothing", func() {
			bkapp.Spec.Processes[0].ResQuotaPlan = ""
			_, err := paasv1alpha2.NewProcResourcesGetter(bkapp).Get("web")
			Expect(err).NotTo(BeNil())
		})
	})
})
