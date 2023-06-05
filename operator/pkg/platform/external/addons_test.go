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

package external

import (
	"bytes"
	"context"
	"encoding/json"
	"io/ioutil"
	"net/http"

	"github.com/google/uuid"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/types"
	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/util/intstr"
)

var _ = Describe("TestClient", func() {
	DescribeTable(
		"test QueryAddonInstance",
		func(handler RoundTripFunc, expectedInstance AddonInstance, expectedError error) {
			client := NewTestClient("foo", "bar", handler)
			instance, err := client.QueryAddonInstance(context.Background(), "", "", "", "")

			if expectedError == nil {
				Expect(err).To(BeNil())
			} else {
				Expect(errors.Is(err, expectedError)).To(BeTrue())
			}
			Expect(instance).To(Equal(expectedInstance))
		},
		Entry("addon found and get 1 extra envs(string)", func(req *http.Request) *http.Response {
			return &http.Response{
				StatusCode: 200,
				Body:       ioutil.NopCloser(bytes.NewBufferString(`{"credentials": {"FAKE_FOO": "FOO"}}`)),
				Header:     make(http.Header),
			}
		}, AddonInstance{Credentials: map[string]intstr.IntOrString{"FAKE_FOO": intstr.Parse("FOO")}}, nil),
		Entry("addon found and get 1 extra envs(int)", func(req *http.Request) *http.Response {
			return &http.Response{
				StatusCode: 200,
				Body:       ioutil.NopCloser(bytes.NewBufferString(`{"credentials": {"FAKE_FOO": 1}}`)),
				Header:     make(http.Header),
			}
		}, AddonInstance{Credentials: map[string]intstr.IntOrString{"FAKE_FOO": intstr.FromInt(1)}}, nil),
		Entry("addon found and get 1 extra envs(string-int)", func(req *http.Request) *http.Response {
			return &http.Response{
				StatusCode: 200,
				Body:       ioutil.NopCloser(bytes.NewBufferString(`{"credentials": {"FAKE_FOO": "1"}}`)),
				Header:     make(http.Header),
			}
		}, AddonInstance{Credentials: map[string]intstr.IntOrString{"FAKE_FOO": intstr.FromString("1")}}, nil),
		Entry("addon found but no extra envs", func(req *http.Request) *http.Response {
			return &http.Response{
				StatusCode: 200,
				Body:       ioutil.NopCloser(bytes.NewBufferString(`{"credentials": {}}`)),
				Header:     make(http.Header),
			}
		}, AddonInstance{Credentials: map[string]intstr.IntOrString{}}, nil),
		Entry("addon not found!", func(req *http.Request) *http.Response {
			return &http.Response{
				StatusCode: 404,
				Body:       ioutil.NopCloser(bytes.NewBufferString(`Not Found`)),
				Header:     make(http.Header),
			}
		}, AddonInstance{}, ErrStatusNotOk),
	)

	DescribeTable(
		"test QueryAddonSpecs",
		func(handler http.RoundTripper, expectedSpecs AddonSpecsResult) {
			client := NewTestClient("", "", handler)
			result, err := client.QueryAddonSpecs(context.Background(), "", "", uuid.New().String())
			Expect(err).To(BeNil())
			Expect(*result).To(Equal(expectedSpecs))
		},
		Entry(
			"return valid specs",
			&SimpleResponse{StatusCode: 200, Body: `{"results": {"version": "5.0.0"}}`},
			AddonSpecsResult{Data: map[string]string{"version": "5.0.0"}},
		),
		Entry(
			"return empty list",
			&SimpleResponse{StatusCode: 200, Body: `{"results": {}}`},
			AddonSpecsResult{Data: make(map[string]string)},
		),
	)

	fakeSvcID := uuid.New().String()
	DescribeTable(
		"test ProvisionAddonInstance",
		func(handler http.RoundTripper, specs AddonSpecs, errMatcher types.GomegaMatcher) {
			client := NewTestClient("", "", handler)
			svcID, err := client.ProvisionAddonInstance(context.Background(), "", "", "", "", specs)
			Expect(err).To(errMatcher)

			if err == nil {
				Expect(svcID).To(Equal(fakeSvcID))
			}
		},
		Entry(
			"200 for provision successfully",
			&SimpleResponse{StatusCode: 200, Body: toJsonString(ProvisionAddonResult{ServiceID: fakeSvcID})},
			AddonSpecs{Specs: map[string]string{"version": "5.0.0"}},
			BeNil(),
		),
		Entry(
			"204 for no need provision",
			&SimpleResponse{StatusCode: 204, Body: toJsonString(ProvisionAddonResult{ServiceID: fakeSvcID})},
			AddonSpecs{},
			BeNil(),
		),
		Entry("404 for addon not found", &SimpleResponse{StatusCode: 404}, AddonSpecs{}, HaveOccurred()),
		Entry("500 for provision failed", &SimpleResponse{StatusCode: 500}, AddonSpecs{}, HaveOccurred()),
	)
})

func toJsonString(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}
