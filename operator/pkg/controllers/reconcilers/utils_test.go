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

package reconcilers

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

var _ = Describe("Test utils", func() {
	var bkapp *v1alpha1.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var fakeDeploy appsv1.Deployment
	ctx := context.Background()

	BeforeEach(func() {
		bkapp = &v1alpha1.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       v1alpha1.KindBkApp,
				APIVersion: v1alpha1.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
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
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(appsv1.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	It("test find extra resource objects", func() {
		a := fakeDeploy
		b := fakeDeploy.DeepCopy()
		b.Name = names.Deployment(bkapp, "web")
		current := []*appsv1.Deployment{&a, b}
		want := resources.GetWantedDeploys(bkapp)

		outdated := FindExtraByName(current, want)
		Expect(len(outdated)).To(Equal(1))
		Expect(outdated[0].Name).To(Equal("bkapp-sample--fake"))
	})

	Context("test UpsertObject", func() {
		DescribeTable(
			"test update with different handleUpdate",
			func(strategy updateHandler[*appsv1.Deployment], updated bool) {
				a := fakeDeploy
				b := fakeDeploy.DeepCopy()
				got := appsv1.Deployment{}

				b.Labels["foo"] = "bar"
				cli := builder.WithObjects(bkapp, &a).Build()

				Expect(UpsertObject(ctx, cli, b, strategy)).NotTo(HaveOccurred())

				_ = cli.Get(ctx, client.ObjectKeyFromObject(&a), &got)

				Expect(equality.Semantic.DeepEqual(got.Labels, b.Labels)).To(Equal(updated))
			},
			Entry("always update", alwaysUpdate[*appsv1.Deployment], true),
			Entry(
				"always forbid update",
				func(ctx context.Context, cli client.Client, current *appsv1.Deployment, want *appsv1.Deployment) error {
					return nil
				},
				false,
			),
			Entry("deployment's handleUpdate", NewDeploymentReconciler(nil).updateHandler, false),
		)

		It("test create object", func() {
			got := appsv1.Deployment{}
			cli := builder.WithObjects(bkapp).Build()

			Expect(apierrors.IsNotFound(cli.Get(ctx, client.ObjectKeyFromObject(&fakeDeploy), &got))).To(BeTrue())
			Expect(UpsertObject(ctx, cli, &fakeDeploy, nil)).NotTo(HaveOccurred())

			_ = cli.Get(ctx, client.ObjectKeyFromObject(&fakeDeploy), &got)

			Expect(got.Spec).To(Equal(fakeDeploy.Spec))
		})
	})
})
