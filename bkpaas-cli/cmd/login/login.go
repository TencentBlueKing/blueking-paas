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

package login

import (
	"fmt"
	"time"

	"github.com/fatih/color"
	"github.com/howeyc/gopass"
	"github.com/pkg/browser"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/account"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// NewCmd create login command
func NewCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "login",
		Short: "Login as user",
		Run: func(cmd *cobra.Command, args []string) {
			userLogin()
		},
	}
}

// 用户登录
func userLogin() {
	color.Cyan("Now we will open your browser...")
	color.Cyan("Please copy and paste the access_token from your browser.")

	// wait 2 seconds for user read tips
	time.Sleep(2 * time.Second)

	if err := browser.OpenURL(config.G.PaaSUrl + "/backend/api/accounts/oauth/token/"); err != nil {
		color.Red("Failed to open browser, error: " + err.Error())
		return
	}

	// read access token implicitly
	fmt.Printf(">>> AccessToken: ")
	accessToken, err := gopass.GetPasswdMasked()
	if err != nil {
		color.Red("Failed to read access token, error: " + err.Error())
		return
	}

	fmt.Printf("User login... ")
	username, err := account.FetchUserNameByAccessToken(string(accessToken))
	if err != nil {
		color.Red("Fail!")
		color.Red(err.Error())
		return
	}

	// update global config and dump to file
	config.G.Username = username
	config.G.AccessToken = string(accessToken)
	if err = config.DumpConf(config.ConfigFilePath); err != nil {
		color.Red("Failed to dump config, error: " + err.Error())
	}
	color.Green("Success!")
}
