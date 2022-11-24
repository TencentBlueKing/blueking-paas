/*
 * Tencent is pleased to support the open source community by making
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

package reconcilers

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

var _ = Describe("Test DeploymentReconciler", func() {
	var bkapp *v1alpha1.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var fakeDeploy appsv1.Deployment

	BeforeEach(func() {
		bkapp = &v1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindBkApp,
				APIVersion: v1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: v1alpha1.AppSpec{
				Processes: []v1alpha1.Process{
					{
						Name:       "web",
						Image:      "nginx:latest",
						Replicas:   v1alpha1.ReplicasTwo,
						TargetPort: 80,
						CPU:        "100m",
						Memory:     "100Mi",
					},
				},
			},
		}

		fakeDeploy = appsv1.Deployment{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "apps/v1",
				Kind:       "Deployment",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name: names.Deployment(bkapp, "fake"),
				// TODO P1 考虑 prod，stag 部署环境隔离？比如不同命名空间？
				Namespace:   bkapp.Namespace,
				Labels:      labels.Deployment(bkapp, "fake"),
				Annotations: make(map[string]string),
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
						Group:   v1alpha1.GroupVersion.Group,
						Version: v1alpha1.GroupVersion.Version,
						Kind:    v1alpha1.KindBkApp,
					}),
				},
			},
			Spec: appsv1.DeploymentSpec{
				Replicas: v1alpha1.ReplicasOne,
				Selector: &metav1.LabelSelector{},
			},
			Status: appsv1.DeploymentStatus{
				Replicas:        1,
				UpdatedReplicas: 1,
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	It("test Reconcile", func() {
		ctx := context.Background()
		outdated := fakeDeploy.DeepCopy()
		// make web deployment look like ready
		web := fakeDeploy.DeepCopy()
		web.Name = names.Deployment(bkapp, "web")
		web.Status.Conditions = append(web.Status.Conditions, appsv1.DeploymentCondition{
			Status: corev1.ConditionTrue,
			Type:   appsv1.DeploymentAvailable,
		})
		cli := builder.WithObjects(bkapp, outdated, web).Build()
		r := DeploymentReconciler{
			Client: cli,
		}

		result := r.Reconcile(ctx, bkapp)
		Expect(result.ShouldAbort()).To(BeFalse())
		// after reconcile, the app phase should be Running
		Expect(bkapp.Status.Phase).To(Equal(v1alpha1.AppRunning))
		// And the outdated deployment should be removed
		Expect(
			apierrors.IsNotFound(
				cli.Get(ctx, types.NamespacedName{Name: outdated.Name, Namespace: outdated.Namespace}, outdated),
			),
		).To(BeTrue())
	})

	Context("test get current state", func() {
		It("not any deployment exists", func() {
			r := DeploymentReconciler{
				Client: builder.Build(),
			}
			deployList, err := r.getCurrentState(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deployList)).To(Equal(0))
		})

		It("with a deployment", func() {
			client := builder.WithObjects(&fakeDeploy).Build()
			r := DeploymentReconciler{
				Client: client,
			}
			deployList, err := r.getCurrentState(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deployList)).To(Equal(1))
		})
	})

	Context("test deploy", func() {
		It("without namesake deployment", func() {
			ctx := context.Background()
			client := builder.Build()
			r := DeploymentReconciler{
				Client: client,
			}
			want := resources.GetWantedDeploys(bkapp)
			Expect(len(want)).To(Equal(1))

			objKey := types.NamespacedName{Name: want[0].Name, Namespace: want[0].Namespace}
			Expect(
				apierrors.IsNotFound(client.Get(ctx, objKey, &appsv1.Deployment{})),
			).To(Equal(true))

			By("update deploy")
			Expect(r.deploy(ctx, want[0])).NotTo(HaveOccurred())

			Expect(
				apierrors.IsNotFound(client.Get(ctx, objKey, &appsv1.Deployment{})),
			).To(Equal(false))
		})

		It("test update", func() {
			ctx := context.Background()
			current := fakeDeploy.DeepCopy()
			current.Annotations[v1alpha1.RevisionAnnoKey] = "1"

			client := builder.WithObjects(bkapp, current).Build()
			r := DeploymentReconciler{Client: client}

			objKey := types.NamespacedName{Name: current.Name, Namespace: current.Namespace}

			By("deploy with same RevisionAnnoKey")
			one := current.DeepCopy()
			one.Spec.Replicas = lo.ToPtr(*one.Spec.Replicas + 1)
			Expect(r.deploy(ctx, one)).NotTo(HaveOccurred())

			got1 := appsv1.Deployment{}
			_ = client.Get(ctx, objKey, &got1)
			Expect(got1.Annotations[v1alpha1.RevisionAnnoKey]).To(Equal("1"))
			Expect(*got1.Spec.Replicas).To(Equal(*one.Spec.Replicas - 1))
			Expect(*current).To(Equal(got1))

			By("deploy with changed RevisionAnnoKey")
			two := fakeDeploy.DeepCopy()
			two.Annotations[v1alpha1.RevisionAnnoKey] = "2"
			Expect(r.deploy(ctx, two)).NotTo(HaveOccurred())

			got2 := appsv1.Deployment{}
			_ = client.Get(ctx, objKey, &got2)
			Expect(got2.Annotations[v1alpha1.RevisionAnnoKey]).To(Equal("2"))
		})
	})
})
