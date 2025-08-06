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

// Package account provide account related functions
package account

import (
	"github.com/TencentBlueKing/gopkg/mapx"
	"github.com/pkg/errors"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// AnonymousUsername 匿名用户名
const AnonymousUsername = "anonymous"

// TokenExpiredOrInvalid Token 过期或无效
var TokenExpiredOrInvalid = errors.New("AccessToken expired or invalid")

// FetchUsernameFailedErr 其他无法获取用户名的情况
var FetchUsernameFailedErr = errors.New("Unable to fetch username")

// FetchUserNameByAccessToken 通过 AccessToken 获取用户名信息
func FetchUserNameByAccessToken(accessToken string) (string, error) {
	authResp, err := apiresources.DefaultRequester.CheckToken(accessToken)

	// 当检查 Token API 不可用时不提前做检查，API 收到无效的 Token 会报错的
	if errors.Is(err, apiresources.CheckTokenApiUnavailable) {
		return AnonymousUsername, nil
	}

	if err != nil {
		return "", err
	}

	if !mapx.GetBool(authResp, "result") {
		return "", TokenExpiredOrInvalid
	}

	if rtx := mapx.GetStr(authResp, "data.id_providers.rtx.username"); rtx != "" {
		return rtx, nil
	}

	if uin := mapx.GetStr(authResp, "data.id_providers.uin.username"); uin != "" {
		return uin, nil
	}
	return "", FetchUsernameFailedErr
}

// IsUserAuthorized 检查用户身份认证情况
func IsUserAuthorized(accessToken string) bool {
	username, err := FetchUserNameByAccessToken(accessToken)
	return username != "" && err == nil
}

// GetOAuthTokenUrl 返回获取 AccessToken 的 API 地址
func GetOAuthTokenUrl() string {
	return config.G.PaaSUrl + "/backend/api/accounts/oauth/token/"
}
