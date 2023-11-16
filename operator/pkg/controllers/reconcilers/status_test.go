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

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/pkg/errors"
	//"github.com/pkg/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
)

var _ = Describe("Test Status", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context
	var oldGeneration int64 = 1
	var newGeneration int64 = 2

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Generation:  newGeneration,
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: paasv1alpha2.AppSpec{Addons: []paasv1alpha2.Addon{{Name: "foo-service"}}},
			Status: paasv1alpha2.AppStatus{
				ObservedGeneration: oldGeneration,
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
		ctx = context.Background()
	})

	It("test update ObservedGeneration", func() {
		Expect(bkapp.Status.ObservedGeneration).To(Equal(oldGeneration))

		ret := Result{}
		UpdateStatus(ctx, builder.WithObjects(bkapp).Build(), bkapp, ret)
		Expect(bkapp.Status.ObservedGeneration).To(Equal(newGeneration))
	})

	It("test not update ObservedGeneration", func() {
		Expect(bkapp.Status.ObservedGeneration).To(Equal(oldGeneration))

		ret := Result{}
		UpdateStatus(
			ctx,
			builder.WithObjects(bkapp).Build(),
			bkapp,
			ret.withError(errors.New("failed to reconcile hook")),
		)
		Expect(bkapp.Status.ObservedGeneration).To(Equal(oldGeneration))
	})
})
