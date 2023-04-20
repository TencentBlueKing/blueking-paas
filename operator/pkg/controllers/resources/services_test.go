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

package resources

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
)

var _ = Describe("test build expect service", func() {
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
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: "default",
						TargetPort:   80,
					},
					{
						Name:         "hi",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: "default",
						TargetPort:   5000,
						Command:      []string{"/bin/sh"},
						Args:         []string{"-c", "echo hi"},
					},
				},
			},
		}
	})

	It("test get web process", func() {
		service := BuildService(bkapp, bkapp.Spec.FindProcess("web"))

		Expect(len(service.Spec.Ports)).To(Equal(1))
		Expect(service.Spec.Ports[0].TargetPort.IntVal).To(Equal(int32(80)))
		Expect(service.Spec.Selector).To(Equal(labels.Deployment(bkapp, "web")))
	})

	It("test get hi process", func() {
		service := BuildService(bkapp, bkapp.Spec.FindProcess("hi"))

		Expect(service).NotTo(BeNil())
		Expect(len(service.Spec.Ports)).To(Equal(1))
		Expect(service.Spec.Ports[0].TargetPort.IntVal).To(Equal(int32(5000)))
		Expect(service.Spec.Selector).To(Equal(labels.Deployment(bkapp, "hi")))
	})

	It("build for missing process", func() {
		service := BuildService(bkapp, bkapp.Spec.FindProcess("hello"))
		Expect(service).To(BeNil())
	})
})
