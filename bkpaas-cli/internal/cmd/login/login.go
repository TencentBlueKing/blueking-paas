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

// Package login provide login command
package login

import (
	"fmt"
	"net/http"
	"time"

	"github.com/fatih/color"
	"github.com/howeyc/gopass"
	"github.com/levigross/grequests"
	"github.com/pkg/browser"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/account"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	cmdUtil "github.com/TencentBlueKing/blueking-paas/client/pkg/utils/cmd"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/console"
)

// NewCmd create login command
func NewCmd() *cobra.Command {
	var useAccessToken, useBkTicket, useBkToken bool

	cmd := &cobra.Command{
		Use:   "login",
		Short: "Login as user",
		RunE: func(cmd *cobra.Command, args []string) error {
			if useAccessToken {
				return loginByAccessToken()
			}
			if useBkTicket {
				return loginByBkTicket()
			}
			if useBkToken {
				return loginByBkToken()
			}
			return loginByBrowser()
		},
		GroupID: cmdUtil.GroupCore.ID,
	}

	cmdUtil.DisableAuthCheck(cmd)
	cmd.Flags().BoolVar(&useAccessToken, "access-token", false, "BlueKing AccessToken")
	cmd.Flags().BoolVar(&useBkTicket, "bk-ticket", false, "BlueKing User Ticket")
	cmd.Flags().BoolVar(&useBkToken, "bk-token", false, "BlueKing User Token")
	return cmd
}

// 通过浏览器登录
func loginByBrowser() error {
	console.Tips("Now we will open your browser...")
	console.Tips("Please copy and paste the access_token from your browser.")

	// waiting for user read tips
	time.Sleep(1 * time.Second)

	if err := browser.OpenURL(account.GetOAuthTokenUrl()); err != nil {
		console.Tips(
			"Don't worry, you can still manually open the browser to get the access_token: %s",
			account.GetOAuthTokenUrl(),
		)
		return errors.Wrap(err, "Failed to open browser")
	}
	return loginByAccessToken()
}

// 通过 AccessToken 登录
func loginByAccessToken() error {
	// read access_token implicitly
	fmt.Printf(">>> AccessToken: ")
	accessToken, err := gopass.GetPasswdMasked()
	if err != nil {
		return errors.Wrap(err, "Failed to read access token")
	}
	return login(string(accessToken))
}

// 通过 bkTicket 进行登录
func loginByBkTicket() error {
	// read bk_ticket implicitly
	fmt.Printf(">>> BkTicket: ")
	bkTicket, err := gopass.GetPasswdMasked()
	if err != nil {
		return errors.Wrap(err, "Failed to read bk ticket")
	}

	resp, err := grequests.Get(account.GetOAuthTokenUrl(), &grequests.RequestOptions{
		Cookies: []*http.Cookie{{Name: "bk_ticket", Value: string(bkTicket)}},
	})
	console.Debug("Response: %d -> %s", resp.StatusCode, resp.String())

	if !resp.Ok || err != nil {
		return errors.New("Failed to get access token by bk ticket")
	}
	respData := map[string]any{}
	if err = resp.JSON(&respData); err != nil {
		return errors.Wrap(err, "Failed to parse oauth api response")
	}
	return login(respData["access_token"].(string))
}

// 通过提供 bkToken 进行登录
func loginByBkToken() error {
	return errors.New("login by bk_token currently unsupported...")
}

// 用户登录
func login(accessToken string) error {
	fmt.Printf("User login... ")
	username, err := account.FetchUserNameByAccessToken(accessToken)
	if err != nil {
		return errors.Wrap(err, "Login Failed")
	}
	// update global config and dump to file
	config.G.Username = username
	config.G.AccessToken = accessToken
	if err = config.DumpConf(config.FilePath); err != nil {
		return errors.Wrap(err, "Login Success but failed to dump config")
	}
	color.Green("Success!")
	return nil
}
