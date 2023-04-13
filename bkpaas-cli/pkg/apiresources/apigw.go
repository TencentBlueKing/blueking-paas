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
	"net/http"

	"github.com/levigross/grequests"
	"github.com/pkg/errors"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// DefaultRequester 默认 API 调用入口
var DefaultRequester Requester = &apigwRequester{}

// 蓝鲸 apigw api 调用入口
type apigwRequester struct{}

// CheckToken 调用 Auth API 检查 accessToken 合法性
func (r apigwRequester) CheckToken(accessToken string) (map[string]any, error) {
	ro := grequests.RequestOptions{
		Params: map[string]string{"access_token": accessToken},
	}
	resp, err := grequests.Get(config.G.CheckTokenUrl, &ro)

	if resp.StatusCode != http.StatusOK || err != nil {
		return nil, AuthApiErr
	}

	respData := map[string]any{}
	if err = resp.JSON(&respData); err != nil {
		return nil, ApiRespDecodeErr
	}
	return respData, nil
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

// GetDefaultAppDeployResult 获取普通应用部署结果
func (r apigwRequester) GetDefaultAppDeployResult(appCode string) (map[string]any, error) {
	// TODO implement me
	panic("implement me")
}

func (r apigwRequester) ListDefaultAppDeployHistory(appCode, appModule string) (map[string]any, error) {
	// TODO implement me
	panic("implement me")
}

// DeployCNativeApp 部署云原生应用
func (r apigwRequester) DeployCNativeApp(
	appCode, appModule, deployEnv string, manifest map[string]any,
) (map[string]any, error) {
	url := fmt.Sprintf(
		"%s/cnative/specs/applications/%s/modules/%s/envs/%s/mres/deployments/",
		config.G.PaaSApigwUrl, appCode, appModule, deployEnv,
	)
	opts := grequests.RequestOptions{Headers: r.headers(), JSON: map[string]any{"manifest": manifest}}
	return r.handlePaaSApiRequest(grequests.Post, url, opts)
}

// GetCNativeAppDeployResult 获取云原生应用部署结果
func (r apigwRequester) GetCNativeAppDeployResult(appCode, appModule, deployEnv string) (map[string]any, error) {
	// TODO implement me
	panic("implement me")
}

func (r apigwRequester) ListCNativeAppDeployHistory(appCode, appModule string) (map[string]any, error) {
	// TODO implement me
	panic("implement me")
}

// 处理 PaaS API 调用请求
func (r apigwRequester) handlePaaSApiRequest(
	reqFunc func(string, *grequests.RequestOptions) (*grequests.Response, error),
	url string, opts grequests.RequestOptions,
) (map[string]any, error) {
	resp, err := reqFunc(url, &opts)

	if err != nil {
		return nil, PaaSApiErr
	}

	// PaaS 平台 API 可能正常返回 200，201，204 等值，这里需要以范围判断（200 <= x < 300）
	if !(http.StatusOK <= resp.StatusCode && resp.StatusCode < http.StatusMultipleChoices) {
		return nil, errors.Errorf("%d -> %s", resp.StatusCode, resp.String())
	}

	respData := map[string]any{}
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
