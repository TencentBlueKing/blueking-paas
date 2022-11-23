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
	"fmt"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
	"bk.tencent.com/paas-app-operator/pkg/testing"
)

var _ = Describe("Test AddonReconciler", func() {
	var bkapp *v1alpha1.BkApp
	var r AddonReconciler
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context

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
		}
		testing.WithAddons(bkapp, "foo-service")

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(v1alpha1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
		ctx = context.Background()
	})

	AfterEach(func() {
		external.SetDefaultClient(nil)
	})

	It("test normal", func() {
		testing.WithAppInfoAnnotations(bkapp)

		r = AddonReconciler{
			Client:         builder.WithObjects(bkapp).Build(),
			ExternalClient: external.NewTestClient("", "", &external.SimpleResponse{StatusCode: 200}),
		}
		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.err).NotTo(HaveOccurred())
		Expect(ret.ShouldAbort()).To(BeFalse())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionTrue))
	})

	It("when not metadata", func() {
		r = AddonReconciler{
			Client:         builder.WithObjects(bkapp).Build(),
			ExternalClient: external.NewTestClient("", "", &external.SimpleResponse{}),
		}
		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.ShouldAbort()).To(BeTrue())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionFalse))
		Expect(cond.Reason).To(Equal("InvalidAnnotations"))
		Expect(cond.Message).To(Equal("InvalidAnnotations: missing bkapp info"))
	})

	It("when extract addons failed", func() {
		testing.WithAppInfoAnnotations(bkapp)
		By("set a invalid addon list", func() {
			bkapp.Annotations[v1alpha1.AddonsAnnoKey] = "['foo-service']"
		})

		r = AddonReconciler{
			Client:         builder.WithObjects(bkapp).Build(),
			ExternalClient: external.NewTestClient("", "", &external.SimpleResponse{StatusCode: 200}),
		}
		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.err).To(HaveOccurred())
		Expect(ret.ShouldAbort()).To(BeTrue())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionFalse))
		Expect(cond.Reason).To(Equal("InvalidAnnotations"))
		Expect(cond.Message).To(Equal("InvalidAnnotations: invalid value for 'bkapp.paas.bk.tencent.com/addons'"))
	})

	It("when provision addon failed", func() {
		testing.WithAppInfoAnnotations(bkapp)
		By("set a failed external client", func() {
			r = AddonReconciler{
				Client:         builder.WithObjects(bkapp).Build(),
				ExternalClient: external.NewTestClient("", "", &external.SimpleResponse{StatusCode: 400, Body: "bar"}),
			}
		})

		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.err).To(HaveOccurred())
		Expect(ret.ShouldAbort()).To(BeTrue())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, v1alpha1.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionFalse))
		Expect(cond.Reason).To(Equal("ProvisionFailed"))
		Expect(
			cond.Message,
		).To(Equal(fmt.Sprintf("ProvisionFailed: failed to provision '%s' instance", "foo-service")))
	})
})
