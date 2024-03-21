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
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/resources"
)

var _ = Describe("Test DeploymentReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var fakeDeploy appsv1.Deployment

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
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
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
				Name:        names.Deployment(bkapp, "fake"),
				Namespace:   bkapp.Namespace,
				Labels:      labels.Deployment(bkapp, "fake"),
				Annotations: make(map[string]string),
				OwnerReferences: []metav1.OwnerReference{
					*metav1.NewControllerRef(bkapp, schema.GroupVersionKind{
						Group:   paasv1alpha2.GroupVersion.Group,
						Version: paasv1alpha2.GroupVersion.Version,
						Kind:    paasv1alpha2.KindBkApp,
					}),
				},
			},
			Spec: appsv1.DeploymentSpec{
				Replicas: paasv1alpha2.ReplicasOne,
				Selector: &metav1.LabelSelector{},
			},
			Status: appsv1.DeploymentStatus{
				Replicas:        1,
				UpdatedReplicas: 1,
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	It("test reconcile", func() {
		ctx := context.Background()
		outdated := fakeDeploy.DeepCopy()
		// make web deployment look like ready
		web := fakeDeploy.DeepCopy()
		web.Name = names.Deployment(bkapp, "web")
		web.Status.Conditions = append(web.Status.Conditions, appsv1.DeploymentCondition{
			Status: corev1.ConditionTrue,
			Type:   appsv1.DeploymentAvailable,
		})
		// Skip the update of deployment when reconciling, otherwise the status of the web deployment will be reset
		// to "pending" and fail the test case.
		web.Annotations[paasv1alpha2.DeploySkipUpdateAnnoKey] = "true"

		cli := builder.WithObjects(bkapp, outdated, web).Build()
		r := NewDeploymentReconciler(cli)

		result := r.Reconcile(ctx, bkapp)
		outdatedKey := types.NamespacedName{Name: outdated.Name, Namespace: outdated.Namespace}
		webKey := types.NamespacedName{Name: web.Name, Namespace: web.Namespace}

		Expect(result.ShouldAbort()).To(BeFalse())
		// after reconcile, the app phase should be Running
		Expect(bkapp.Status.Phase).To(Equal(paasv1alpha2.AppRunning))
		Expect(apierrors.IsNotFound(cli.Get(ctx, outdatedKey, &appsv1.Deployment{}))).To(BeTrue())
		Expect(cli.Get(ctx, webKey, &appsv1.Deployment{})).To(Not(HaveOccurred()))

		By("Reconcile and check the deployments again")
		result = r.Reconcile(ctx, bkapp)
		Expect(result.ShouldAbort()).To(BeFalse())
		Expect(apierrors.IsNotFound(cli.Get(ctx, outdatedKey, &appsv1.Deployment{}))).To(BeTrue())
		Expect(cli.Get(ctx, webKey, &appsv1.Deployment{})).To(Not(HaveOccurred()))
	})

	Context("test get old deployments", func() {
		It("no deployment", func() {
			r := NewDeploymentReconciler(builder.Build())
			deployList, err := r.getCurrentDeployments(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deployList)).To(Equal(0))
		})

		It("one deployment", func() {
			client := builder.WithObjects(&fakeDeploy).Build()
			r := NewDeploymentReconciler(client)
			deployList, err := r.getCurrentDeployments(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(deployList)).To(Equal(1))
		})
	})

	Context("test getNewDeployments", func() {
		var ctx context.Context
		var client client.Client
		var r *DeploymentReconciler

		BeforeEach(func() {
			ctx = context.Background()
			client = builder.Build()
			r = NewDeploymentReconciler(client)
		})

		// A shortcut function to get the old deployments
		oldDeployments := func() []*appsv1.Deployment {
			deployList, _ := r.getCurrentDeployments(ctx, bkapp)
			return deployList
		}

		It("without any deployments", func() {
			r := NewDeploymentReconciler(client)
			want, _ := resources.BuildProcDeployment(bkapp, "web")

			By("The web deployment should not exists")
			objKey := types.NamespacedName{Name: want.Name, Namespace: want.Namespace}
			Expect(apierrors.IsNotFound(client.Get(ctx, objKey, &appsv1.Deployment{}))).To(BeTrue())

			By("Call getNewDeployments with an empty old deployment list to create the resources")
			newDeployMap, err := r.getNewDeployments(ctx, bkapp, nil)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(newDeployMap)).To(Equal(1))
			Expect(client.Get(ctx, objKey, &appsv1.Deployment{})).To(Not(HaveOccurred()))
		})

		It("update existing deployment, integrated", func() {
			// Create the deployment first
			_, _ = r.getNewDeployments(ctx, bkapp, oldDeployments())

			By("Validate the replicas of the deployment")
			d := appsv1.Deployment{}
			want, _ := resources.BuildProcDeployment(bkapp, "web")
			objKey := types.NamespacedName{Name: want.Name, Namespace: want.Namespace}
			_ = client.Get(ctx, objKey, &d)
			Expect(*d.Spec.Replicas).To(Equal(int32(2)))
			lastRV := d.ResourceVersion

			By("Increase the replicas and get new deployments")
			*bkapp.Spec.Processes[0].Replicas = 3
			_, _ = r.getNewDeployments(ctx, bkapp, oldDeployments())
			_ = client.Get(ctx, objKey, &d)
			Expect(*d.Spec.Replicas).To(Equal(int32(3)))
			// The resourceVersion should be updated
			Expect(d.ResourceVersion > lastRV).To(BeTrue())
			lastRV = d.ResourceVersion

			By("Get new deployments without any changes on the bkapp")
			_, _ = r.getNewDeployments(ctx, bkapp, oldDeployments())
			_ = client.Get(ctx, objKey, &d)
			// The resourceVersion should remains the same because no updates happened
			Expect(d.ResourceVersion == lastRV).To(BeTrue())
		})

		It("update existing deployment that has no serialized bkapp", func() {
			// Create the deployment, update it to remove the annotation
			_, _ = r.getNewDeployments(ctx, bkapp, oldDeployments())
			d := appsv1.Deployment{}
			want, _ := resources.BuildProcDeployment(bkapp, "web")
			objKey := types.NamespacedName{Name: want.Name, Namespace: want.Namespace}
			_ = client.Get(ctx, objKey, &d)
			Expect(d.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]).NotTo(BeEmpty())

			// Remove the annotation
			delete(d.Annotations, paasv1alpha2.LastSyncedSerializedBkAppAnnoKey)
			_ = client.Update(ctx, &d)
			updatedDeploy := appsv1.Deployment{}
			_ = client.Get(ctx, objKey, &updatedDeploy)
			Expect(updatedDeploy.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]).To(BeEmpty())

			By("Get new deployments should set the annotation back")
			_, _ = r.getNewDeployments(ctx, bkapp, oldDeployments())
			_ = client.Get(ctx, objKey, &d)
			Expect(d.Annotations[paasv1alpha2.LastSyncedSerializedBkAppAnnoKey]).NotTo(BeEmpty())
		})
	})
})
