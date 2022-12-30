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
	"fmt"
	"net/http"
	"reflect"

	"gopkg.in/yaml.v3"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestClient", func() {
	var ctx context.Context

	BeforeEach(func() {
		ctx = context.Background()
	})

	DescribeTable("test path join", func(endpoint, expected string) {
		client := NewTestClient("foo", "bar", RoundTripFunc(func(req *http.Request) *http.Response {
			return nil
		}))
		req, err := client.NewRequest(ctx, "GET", endpoint, bytes.NewBuffer([]byte{}))
		Expect(err).To(Not(HaveOccurred()))
		Expect(req.URL.Path).To(Equal(expected))
	},
		Entry("with / prefix", "/the/url/path", fakeURL.Path+"/the/url/path"),
		Entry("without / prefix", "the/url/path", fakeURL.Path+"/the/url/path"),
	)

	It("validate the header authorization", func() {
		var header http.Header
		client := NewTestClient("foo", "bar", RoundTripFunc(func(req *http.Request) *http.Response {
			header = req.Header
			return nil
		}))
		req, err := client.NewRequest(ctx, "GET", "dummy", bytes.NewBuffer([]byte{}))

		Expect(err).To(Not(HaveOccurred()))
		client.Do(req)
		Expect(
			header.Get(AuthorizationHeaderKey),
		).To(Equal(fmt.Sprintf("{\"bk_app_code\": \"%s\", \"bk_app_secret\": \"%s\"}", "foo", "bar")))
	})
})

var _ = Describe("TestResult", func() {
	type Dummy struct {
		Foo string
		Bar string `yaml:"the_bar" json:"the_bar"`
	}

	DescribeTable("test transfer body into any structure", func(body []byte, decoder decoder, expected any) {
		instance := Dummy{}
		result := Result{
			body: body,
		}
		Expect(result.Into(&instance, decoder)).NotTo(HaveOccurred())
		Expect(instance).To(Equal(expected))
	},
		Entry("test json format", []byte(`{"foo": "1", "the_bar": "2"}`), json.Unmarshal, Dummy{"1", "2"}),
		Entry("test yaml format", []byte("foo: \"3\"\nthe_bar: \"4\""), yaml.Unmarshal, Dummy{"3", "4"}),
	)

	It("test unmarshal error", func() {
		instance := Dummy{}
		result := Result{
			body: []byte(`{"foo": 1, "bar": 2}`),
		}
		err := result.Into(&instance, json.Unmarshal)
		Expect(reflect.TypeOf(err)).To(Equal(reflect.TypeOf(&json.UnmarshalTypeError{})))
	})
})
