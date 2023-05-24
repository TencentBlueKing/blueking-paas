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
	"bytes"
	"context"
	"fmt"
	"io/ioutil"
	"net/http"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
	"bk.tencent.com/paas-app-operator/pkg/testing"
)

var _ = Describe("Test AddonReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var r *AddonReconciler
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var ctx context.Context

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
			Spec: paasv1alpha2.AppSpec{Addons: []paasv1alpha2.Addon{{Name: "foo-service"}}},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
		ctx = context.Background()
	})

	AfterEach(func() {
		external.SetDefaultClient(nil)
	})

	It("test normal", func() {
		testing.WithAppInfoAnnotations(bkapp)

		r = &AddonReconciler{
			Client: builder.WithObjects(bkapp).Build(),
			ExternalClient: external.NewTestClient(
				"", "", external.RoundTripFunc(func(req *http.Request) *http.Response {
					switch req.Method {
					case http.MethodGet:
						// mock QueryAddonSpecs
						return &http.Response{
							StatusCode: 200,
							Body: ioutil.NopCloser(
								bytes.NewBufferString(`{"results": [{"name": "version", "value": "5.0.0"}]}`),
							),
							Header: make(http.Header),
						}
					case http.MethodPost:
						// mock ProvisionAddonInstance
						return &http.Response{
							StatusCode: 200,
							Body:       ioutil.NopCloser(bytes.NewBufferString(`{"service_id": "foo-id"}`)),
							Header:     make(http.Header),
						}
					default:
						return &http.Response{
							StatusCode: 400,
							Body:       ioutil.NopCloser(bytes.NewBufferString(``)),
							Header:     make(http.Header),
						}
					}
				}),
			),
		}
		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.err).NotTo(HaveOccurred())
		Expect(ret.ShouldAbort()).To(BeFalse())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionTrue))
		Expect(bkapp.Status.AddonStatuses[0].Name).To(Equal("foo-service"))
		Expect(bkapp.Status.AddonStatuses[0].State).To(Equal(paasv1alpha2.AddonProvisioned))
		Expect(
			bkapp.Status.AddonStatuses[0].Specs[0],
		).To(Equal(paasv1alpha2.AddonSpec{Name: "version", Value: "5.0.0"}))
	})

	It("when not metadata", func() {
		r = &AddonReconciler{
			Client:         builder.WithObjects(bkapp).Build(),
			ExternalClient: external.NewTestClient("", "", &external.SimpleResponse{}),
		}
		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.ShouldAbort()).To(BeTrue())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionFalse))
		Expect(cond.Reason).To(Equal("InternalServerError"))
		Expect(cond.Message).To(Equal(
			"InvalidAnnotations: missing bkapp info, detail: " +
				"for missing bkapp.paas.bk.tencent.com/region: unable to parse app metadata",
		))
	})

	It("when provision addon failed", func() {
		testing.WithAppInfoAnnotations(bkapp)

		failMessage := "no available resource can provide"
		By("set a failed external client", func() {
			r = &AddonReconciler{
				Client: builder.WithObjects(bkapp).Build(),
				ExternalClient: external.NewTestClient(
					"",
					"",
					&external.SimpleResponse{
						StatusCode: 400,
						Body:       failMessage,
						Header:     http.Header{"Content-Type": []string{"application/json"}},
					},
				),
			}
		})

		ret := r.Reconcile(ctx, bkapp)

		Expect(ret.err).To(HaveOccurred())
		Expect(ret.ShouldAbort()).To(BeTrue())

		cond := apimeta.FindStatusCondition(bkapp.Status.Conditions, paasv1alpha2.AddOnsProvisioned)
		Expect(cond.Status).To(Equal(metav1.ConditionFalse))
		Expect(cond.Reason).To(Equal("InternalServerError"))
		Expect(cond.Message).To(Equal(
			fmt.Sprintf("Addon 'foo-service' provision failed, detail: %s: response not ok", failMessage),
		))
		Expect(bkapp.Status.AddonStatuses[0].State).To(Equal(paasv1alpha2.AddonFailed))
	})
})
