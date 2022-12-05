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
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"path"
	"strings"

	"golang.org/x/net/http2"
)

var defaultClient *Client

// AuthorizationHeaderKey 是在请求中存储网关鉴权信息的 Key
const AuthorizationHeaderKey = "X-Bkapi-Authorization"

var (
	// ErrClientUnconfigured 未初始化 DefaultClient, 表示当前 operator 不支持访问 bkpaas 服务
	ErrClientUnconfigured = errors.New("the DefaultClient is unconfigured")
	// ErrStatusNotOk return when the status code not equal to 2xx
	ErrStatusNotOk = errors.New("response not ok")
)

type decoder func([]byte, any) error

// Result contains the result of calling Request.Do().
type Result struct {
	body        []byte
	contentType string
	err         error
	statusCode  int
}

// Into stores the result into obj, if possible. If obj is nil it is ignored.
func (r Result) Into(obj any, decoder decoder) error {
	if r.err != nil {
		return r.err
	}

	if decoder == nil {
		decoder = json.Unmarshal
	}

	err := decoder(r.body, obj)
	return err
}

// Client follow the authenticate conventions of Blueking API Gateway.
// The baseURL is expected to point to an HTTP or HTTPS path that
// is the Gateway URL of a Blueking API Gateway.
type Client struct {
	appCode   string
	appSecret string
	// base is the root URL for all invocations of the client
	base url.URL
	// Set specific behavior of the client.  If not set http.DefaultClient will be used.
	Client *http.Client
}

// NewClient creates a new Client. This client performs generic REST functions
// such as Get, Put, Post, and Delete on specified paths.
func NewClient(baseURL *url.URL, appCode, appSecret string, client *http.Client) *Client {
	base := *baseURL
	if !strings.HasSuffix(base.Path, "/") {
		base.Path += "/"
	}
	base.RawQuery = ""
	base.Fragment = ""

	return &Client{
		appCode:   appCode,
		appSecret: appSecret,
		base:      base,
		Client:    client,
	}
}

// NewRequest creates a new http.Request object for accessing the Gateway.
func (c *Client) NewRequest(ctx context.Context, method, endpoint string, body io.Reader) (*http.Request, error) {
	finalURL := c.base
	finalURL.Path = path.Join(c.base.Path, endpoint)
	return http.NewRequestWithContext(ctx, method, finalURL.String(), body)
}

// Do formats and executes the request. Returns a Result object for easy response
// processing.
//
// Error type:
//  * http.Client.Do errors are returned directly.
func (c *Client) Do(req *http.Request) Result {
	// 设置蓝鲸网关的认证信息
	req.Header.Set(
		AuthorizationHeaderKey,
		fmt.Sprintf("{\"bk_app_code\": \"%s\", \"bk_app_secret\": \"%s\"}", c.appCode, c.appSecret),
	)
	// 发送请求到后端
	resp, err := c.Client.Do(req)
	if err != nil {
		return Result{
			err: err,
		}
	}
	return c.transformResponse(resp, req)
}

// transformResponse converts an API response into a structured API object
func (c *Client) transformResponse(resp *http.Response, req *http.Request) Result {
	var body []byte
	if resp.Body != nil {
		defer resp.Body.Close()

		data, err := ioutil.ReadAll(resp.Body)
		switch err.(type) {
		case nil:
			body = data
		case http2.StreamError:
			// This is trying to catch the scenario that the server may close the connection when sending the
			// response body. This can be caused by server timeout due to a slow network connection.
			streamErr := fmt.Errorf("stream error when reading response body, may be caused by closed connection. Please retry. Original error: %w", err)
			return Result{
				err: streamErr,
			}
		default:
			unexpectedErr := fmt.Errorf("unexpected error when reading response body. Please retry. Original error: %w", err)
			return Result{
				err: unexpectedErr,
			}
		}
	}
	contentType := resp.Header.Get("Content-Type")
	statusCode := resp.StatusCode
	var err error

	if !(statusCode >= http.StatusOK && statusCode < http.StatusMultipleChoices) {
		err = ErrStatusNotOk
		if contentType == "application/json" {
			err = fmt.Errorf("%w: %s", err, string(body))
		}
	}

	return Result{
		body:        body,
		contentType: contentType,
		statusCode:  resp.StatusCode,
		err:         err,
	}
}

// GetDefaultClient is used to get default bkpaas client
func GetDefaultClient() (*Client, error) {
	if defaultClient == nil {
		return nil, ErrClientUnconfigured
	}
	return defaultClient, nil
}

// SetDefaultClient is used to set the default bkpaas client
func SetDefaultClient(client *Client) {
	defaultClient = client
}
