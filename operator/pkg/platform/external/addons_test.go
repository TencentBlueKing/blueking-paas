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
	"io/ioutil"
	"net/http"

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

	DescribeTable("test ProvisionAddonInstance", func(handler http.RoundTripper, errMatcher types.GomegaMatcher) {
		client := NewTestClient("", "", handler)
		err := client.ProvisionAddonInstance(context.Background(), "", "", "", "")
		Expect(err).To(errMatcher)
	}, Entry("200 for provision successfully", &SimpleResponse{StatusCode: 200}, BeNil()),
		Entry("204 for no need provision", &SimpleResponse{StatusCode: 204}, BeNil()),
		Entry("404 for addon not found", &SimpleResponse{StatusCode: 404}, HaveOccurred()),
		Entry("500 for provision failed", &SimpleResponse{StatusCode: 500}, HaveOccurred()),
	)
})
