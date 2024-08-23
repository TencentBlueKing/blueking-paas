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

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
)

var _ = Describe("Test ServiceReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var fakeService *corev1.Service
	ctx := context.Background()

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
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
				},
			},
		}

		fakeService = &corev1.Service{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "v1",
				Kind:       "Service",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        names.Deployment(bkapp, "fake"),
				Namespace:   bkapp.Namespace,
				Labels:      labels.Deployment(bkapp, "fake"),
				Annotations: make(map[string]string),
			},
			Spec: corev1.ServiceSpec{
				Ports: []corev1.ServicePort{
					{
						Name:       "http",
						Port:       80,
						TargetPort: intstr.FromInt(80),
						Protocol:   corev1.ProtocolTCP,
					},
				},
				Selector: labels.Deployment(bkapp, "fake"),
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	It("test Reconcile", func() {
		outdated := fakeService.DeepCopy()
		web := fakeService.DeepCopy()
		web.Name = names.Service(bkapp, "web")
		r := NewServiceReconciler(builder.WithObjects(outdated).Build())

		result := r.Reconcile(context.Background(), bkapp)
		Expect(result.ShouldAbort()).To(BeFalse())

		got := corev1.ServiceList{}
		_ = r.Client.List(ctx, &got)
		Expect(len(got.Items)).To(Equal(1))
		Expect(got.Items[0].Name).To(Equal(names.Service(bkapp, "web")))
	})

	Context("test get current state", func() {
		It("not any Service exists", func() {
			r := NewServiceReconciler(builder.Build())
			svcList, err := r.listCurrentServices(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(svcList)).To(Equal(0))
		})

		It("with a Service", func() {
			client := builder.WithObjects(fakeService).Build()
			r := NewServiceReconciler(client)
			svcList, err := r.listCurrentServices(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(svcList)).To(Equal(1))
		})
	})

	It("test getWantedService", func() {
		r := NewServiceReconciler(builder.Build())
		svcList := r.getWantedService(bkapp)

		Expect(len(svcList)).To(Equal(1))
		Expect(svcList[0].Name).To(Equal(names.Service(bkapp, "web")))
	})

	It("test handleUpdate", func() {
		current := fakeService.DeepCopy()
		want := fakeService.DeepCopy()
		cli := builder.WithObjects(current).Build()
		r := NewServiceReconciler(cli)

		Expect(r.handleUpdate(ctx, cli, current, want)).NotTo(HaveOccurred())

		serviceLookupKey := types.NamespacedName{Namespace: current.GetNamespace(), Name: current.GetName()}
		got1 := corev1.Service{}
		_ = cli.Get(ctx, serviceLookupKey, &got1)

		Expect(got1.Spec.Selector).To(Equal(current.Spec.Selector))
		Expect(got1.Spec.Ports).To(Equal(current.Spec.Ports))

		By("change Service.Spec")
		want.Spec.Selector[paasv1alpha2.ProcessNameKey] = "web"

		Expect(want.Spec.Selector).NotTo(Equal(current.Spec.Selector))
		Expect(r.handleUpdate(ctx, cli, current, want)).NotTo(HaveOccurred())

		got2 := corev1.Service{}
		_ = cli.Get(ctx, serviceLookupKey, &got2)

		Expect(got2.Spec.Selector).NotTo(Equal(got1.Spec.Selector))
		Expect(got2.Spec.Selector).To(Equal(want.Spec.Selector))
	})
})

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
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
					{
						Name:         "hi",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
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
		Expect(service.Labels).To(Equal(labels.Deployment(bkapp, "web")))
		Expect(service.Spec.Selector).To(Equal(labels.PodSelector(bkapp, "web")))
	})

	It("test get hi process", func() {
		service := BuildService(bkapp, bkapp.Spec.FindProcess("hi"))

		Expect(service).NotTo(BeNil())
		Expect(len(service.Spec.Ports)).To(Equal(1))
		Expect(service.Spec.Ports[0].TargetPort.IntVal).To(Equal(int32(5000)))
		Expect(service.Labels).To(Equal(labels.Deployment(bkapp, "hi")))
		Expect(service.Spec.Selector).To(Equal(labels.PodSelector(bkapp, "hi")))
	})

	It("build for missing process", func() {
		service := BuildService(bkapp, bkapp.Spec.FindProcess("hello"))
		Expect(service).To(BeNil())
	})
})

var _ = Describe("test build expect service by proc services", func() {
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
				Annotations: map[string]string{paasv1alpha2.ProcServicesFeatureEnabledAnnoKey: "true"},
			},
		}
	})

	It("build with proc services", func() {
		procName := "web"
		bkapp.Spec = paasv1alpha2.AppSpec{
			Processes: []paasv1alpha2.Process{
				{
					Name:         procName,
					Replicas:     paasv1alpha2.ReplicasTwo,
					ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
					Services: []paasv1alpha2.ProcService{
						{
							Name:        "web",
							TargetPort:  5000,
							Protocol:    corev1.ProtocolTCP,
							ExposedType: &paasv1alpha2.ExposedType{Name: paasv1alpha2.ExposedTypeNameBkHttp},
							Port:        80,
						},
						{
							Name:       "metric",
							TargetPort: 5001,
							Protocol:   corev1.ProtocolTCP,
							Port:       5001,
						},
					},
				},
			},
		}

		service := BuildService(bkapp, bkapp.Spec.FindProcess(procName))
		Expect(service.Spec.Ports).To(Equal([]corev1.ServicePort{
			{
				Name:       "web",
				TargetPort: intstr.FromInt(5000),
				Protocol:   corev1.ProtocolTCP,
				Port:       80,
			},
			{
				Name:       "metric",
				TargetPort: intstr.FromInt(5001),
				Protocol:   corev1.ProtocolTCP,
				Port:       5001,
			},
		}))
		Expect(service.Labels).To(Equal(labels.Deployment(bkapp, procName)))
		Expect(service.Spec.Selector).To(Equal(labels.PodSelector(bkapp, procName)))
	})

	It("build without proc services", func() {
		bkapp.Spec = paasv1alpha2.AppSpec{
			Processes: []paasv1alpha2.Process{
				{
					Name:         "web",
					Replicas:     paasv1alpha2.ReplicasTwo,
					ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
				},
			},
		}

		service := BuildService(bkapp, bkapp.Spec.FindProcess("web"))
		Expect(service).To(BeNil())
	})
})
