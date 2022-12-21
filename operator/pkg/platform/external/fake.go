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
	"io/ioutil"
	"net/http"
	"net/url"
)

var fakeURL *url.URL

// RoundTripFunc is an implement of RoundTripper interface
type RoundTripFunc func(req *http.Request) *http.Response

// RoundTrip executes a single HTTP transaction, returning
// a Response for the provided Request.
func (f RoundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req), nil
}

// SimpleResponse  is an implement of RoundTripper interface
// will always return a *http.Response with the same value of SimpleResponse
type SimpleResponse struct {
	StatusCode int
	Body       string
	Header     http.Header
}

// RoundTrip ...
func (r *SimpleResponse) RoundTrip(req *http.Request) (*http.Response, error) {
	header := r.Header
	if header == nil {
		header = make(http.Header)
	}
	return &http.Response{
		StatusCode: r.StatusCode,
		Body:       ioutil.NopCloser(bytes.NewBufferString(r.Body)),
		Header:     header,
	}, nil
}

// NewTestClient return a dummy Client will handle all request by the given `f`
func NewTestClient(appCode, appSecret string, f http.RoundTripper) *Client {
	return NewClient(
		fakeURL, appCode, appSecret, &http.Client{
			Transport: f,
		})
}

func init() {
	fakeURL, _ = url.Parse("https://example.com/baz")
}
