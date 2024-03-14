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

package apiresources

import (
	"fmt"
	"strings"

	"github.com/levigross/grequests"
	"github.com/pkg/errors"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/console"
)

// CheckTokenApiUnavailable CheckToken API 不可用
var CheckTokenApiUnavailable = errors.New("Check token api unavailable")

// DefaultRequester 默认 API 调用入口
var DefaultRequester Requester = &apigwRequester{}

// 蓝鲸 apigw api 调用入口
type apigwRequester struct{}

// CheckToken 调用 Auth API 检查 accessToken 合法性
func (r apigwRequester) CheckToken(accessToken string) (map[string]any, error) {
	// 如果 CheckTokenUrl 未配置，则认为该环境不支持通过 accessToken 获取用户身份
	// 会默认跳过身份检查，直接用 accessToken 请求对应的 API，若无效或过期则 API 返回错误
	if config.G.CheckTokenUrl == "" {
		return nil, CheckTokenApiUnavailable
	}

	ro := grequests.RequestOptions{
		Params: map[string]string{"access_token": accessToken},
	}
	console.Debug("Request Url: %s, Params: %v", config.G.CheckTokenUrl, ro.Params)

	resp, err := grequests.Get(config.G.CheckTokenUrl, &ro)
	console.Debug("Response %d -> %s", resp.StatusCode, resp.String())

	if !resp.Ok || err != nil {
		return nil, AuthApiErr
	}

	respData := map[string]any{}
	if err = resp.JSON(&respData); err != nil {
		return nil, ApiRespDecodeErr
	}
	return respData, nil
}

func (r apigwRequester) ListAppMinimal() (map[string]any, error) {
	url := fmt.Sprintf("%s/bkapps/applications/lists/minimal/", config.G.PaaSApigwUrl)
	return r.handlePaaSApiRequest(grequests.Get, url, grequests.RequestOptions{Headers: r.headers()})
}

// GetAppInfo 获取应用基础信息
func (r apigwRequester) GetAppInfo(appCode string) (map[string]any, error) {
	url := fmt.Sprintf("%s/bkapps/applications/%s/", config.G.PaaSApigwUrl, appCode)
	return r.handlePaaSApiRequest(grequests.Get, url, grequests.RequestOptions{Headers: r.headers()})
}

// DeployDefaultApp 部署普通应用
func (r apigwRequester) DeployDefaultApp(appCode, appModule, deployEnv, branch string) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/bkapps/applications/%s/modules/%s/envs/%s/deployments/",
		config.G.PaaSApigwUrl, appCode, appModule, deployEnv,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), JSON: map[string]string{
		"version_type": "branch", "version_name": branch, "revision": branch, // 暂不支持按 commit_id 拉取代码
	}}
	return r.handlePaaSApiRequest(grequests.Post, url, opts)
}

// GetAppDeployResult 获取应用部署结果
func (r apigwRequester) GetAppDeployResult(appCode, appModule, deployID string) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/bkapps/applications/%s/modules/%s/deployments/%s/result/",
		config.G.PaaSApigwUrl, appCode, appModule, deployID,
	)
	return r.handlePaaSApiRequest(grequests.Get, url, grequests.RequestOptions{Headers: r.headers()})
}

func (r apigwRequester) ListAppDeployHistory(appCode, appModule string) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/bkapps/applications/%s/modules/%s/deployments/lists/",
		config.G.PaaSApigwUrl, appCode, appModule,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), Params: map[string]string{"limit": "5"}}
	return r.handlePaaSApiRequest(grequests.Get, url, opts)
}

// DeployCNativeApp 部署云原生应用
func (r apigwRequester) DeployCNativeApp(
	appCode, appModule, deployEnv string, manifest map[string]any, tag string, branch string,
) (map[string]any, error) {
	if manifest != nil {
		// 导入 manifest
		_, err := r.ImportManifest(appCode, appModule, manifest)
		if err != nil {
			return nil, err
		}
		if tag == "" {
			tag = "latest"
		}
		// 从 manifest 中提取 tag 信息
		if spec, ok := manifest["spec"].(map[string]any); ok {
			if build, ok := spec["build"].(map[string]any); ok {
				if image, ok := build["image"].(string); ok {
					// 从 image 中提取 tag 信息
					if pos := strings.LastIndex(image, ":"); pos != -1 {
						tag = image[pos+1:]
					}
				}
			}
		}
	}
	var data map[string]any
	if manifest != nil || tag != "" {
		data = map[string]any{"version_type": "image", "version_name": tag}
	} else if branch != "" {
		data = map[string]any{"version_type": "branch", "version_name": branch}
	} else {
		return nil, errors.New("branch or manifest or tag is required")
	}

	url := fmt.Sprintf(
		"%s/bkapps/applications/%s/modules/%s/envs/%s/deployments/",
		config.G.PaaSApigwUrl, appCode, appModule, deployEnv,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), JSON: data}
	return r.handlePaaSApiRequest(grequests.Post, url, opts)
}

func (r apigwRequester) ImportManifest(
	appCode, appModule string, manifest map[string]any,
) ([]map[string]any, error) {
	url := fmt.Sprintf(
		"%s/bkapps/applications/%s/modules/%s/bkapp_model/manifests/current/",
		config.G.PaaSApigwUrl, appCode, appModule,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), JSON: map[string]any{"manifest": manifest}}
	return r.handleListPaaSApiRequest(grequests.Put, url, opts)
}

// GetCNativeAppDeployResult 获取云原生应用部署结果
func (r apigwRequester) GetCNativeAppDeployResult(appCode, appModule, deployEnv string) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/cnative/specs/applications/%s/modules/%s/envs/%s/mres/status/",
		config.G.PaaSApigwUrl, appCode, appModule, deployEnv,
	)
	return r.handlePaaSApiRequest(grequests.Get, url, grequests.RequestOptions{Headers: r.headers()})
}

func (r apigwRequester) ListCNativeAppDeployHistory(appCode, appModule, deployEnv string) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/cnative/specs/applications/%s/modules/%s/envs/%s/mres/deployments/",
		config.G.PaaSApigwUrl, appCode, appModule, deployEnv,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), Params: map[string]string{"limit": "5"}}
	return r.handlePaaSApiRequest(grequests.Get, url, opts)
}

type gReqFunc func(string, *grequests.RequestOptions) (*grequests.Response, error)

// 处理 PaaS API 调用请求
func (r apigwRequester) handlePaaSApiRequest(
	reqFunc gReqFunc, url string, opts grequests.RequestOptions,
) (map[string]any, error) {
	console.Debug("Request Url: %s, Headers: %v, Params: %v, Body: %v", url, opts.Headers, opts.Params, opts.JSON)

	resp, err := reqFunc(url, &opts)
	if err != nil {
		return nil, PaaSApiErr
	}

	console.Debug("Response %d -> %s", resp.StatusCode, resp.String())

	if !resp.Ok {
		return nil, errors.Errorf("%d -> %s", resp.StatusCode, resp.String())
	}

	respData := map[string]any{}
	if err = resp.JSON(&respData); err != nil {
		return nil, ApiRespDecodeErr
	}
	return respData, nil
}

// 处理 PaaS API 调用请求(返回值为 list )
func (r apigwRequester) handleListPaaSApiRequest(
	reqFunc gReqFunc, url string, opts grequests.RequestOptions,
) ([]map[string]any, error) {
	console.Debug("Request Url: %s, Headers: %v, Params: %v, Body: %v", url, opts.Headers, opts.Params, opts.JSON)

	resp, err := reqFunc(url, &opts)
	if err != nil {
		return nil, PaaSApiErr
	}

	console.Debug("Response %d -> %s", resp.StatusCode, resp.String())

	if !resp.Ok {
		return nil, errors.Errorf("%d -> %s", resp.StatusCode, resp.String())
	}

	var respData []map[string]any
	if err = resp.JSON(&respData); err != nil {
		return nil, ApiRespDecodeErr
	}
	return respData, nil
}

// 生成访问 apigw 需要的 headers 信息
func (r apigwRequester) headers() map[string]string {
	return map[string]string{
		"Content-Type":          "application/json",
		"X-BKAPI-AUTHORIZATION": fmt.Sprintf("{\"access_token\": \"%s\"}", config.G.AccessToken),
	}
}
