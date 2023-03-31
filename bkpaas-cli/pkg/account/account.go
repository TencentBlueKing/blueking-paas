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

package account

import (
	"encoding/json"

	"github.com/TencentBlueKing/gopkg/mapx"
	"github.com/parnurzeal/gorequest"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// IsUserAuthorized 检查用户认证情况（AccessToken 准确 & 未过期 & 身份与 Username 一致）
func IsUserAuthorized() bool {
	resp, body, errs := gorequest.New().
		Get(config.G.CheckTokenUrl).
		Param("access_token", config.G.AccessToken).
		End()

	if resp.StatusCode != 200 || errs != nil {
		return false
	}

	authResp := map[string]any{}
	if err := json.Unmarshal([]byte(body), &authResp); err != nil {
		return false
	}

	if !mapx.GetBool(authResp, "result") {
		return false
	}

	rtx := mapx.GetStr(authResp, "data.id_providers.rtx.username")
	uin := mapx.GetStr(authResp, "data.id_providers.uin.username")
	// 兼容两种鉴权身份，任意身份一致即允许通过
	if rtx != config.G.Username && uin != config.G.Username {
		return false
	}
	return true
}
