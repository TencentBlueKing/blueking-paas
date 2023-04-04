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
	"net/http"

	"github.com/levigross/grequests"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// 蓝鲸 apigw api 调用入口
type apigwRequester struct{}

func (r apigwRequester) CheckToken(accessToken string) (map[string]any, error) {
	ro := grequests.RequestOptions{
		Params: map[string]string{"access_token": accessToken},
	}
	resp, err := grequests.Get(config.G.CheckTokenUrl, &ro)

	if resp.StatusCode != http.StatusOK || err != nil {
		return nil, AuthApiErr
	}

	authResp := map[string]any{}
	if err = resp.JSON(&authResp); err != nil {
		return nil, AuthApiRespErr
	}
	return authResp, nil
}

// DefaultRequester 默认 API 调用入口
var DefaultRequester Requester = &apigwRequester{}
