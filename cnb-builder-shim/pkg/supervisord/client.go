/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */
package supervisord

import (
	"context"
	"fmt"
	"os/exec"
	"time"

	"github.com/kolo/xmlrpc"
	"github.com/pkg/errors"
)

type Client struct {
	rpcClient *xmlrpc.Client
	config    ClientConfig
}

type ClientConfig struct {
	RPCAddress string // XML-RPC 地址
	ConfigPath string // Supervisord 启动配置路径
}

func NewClient(cfg ClientConfig) (*Client, error) {
	client := &Client{config: cfg}

	// 尝试连接, 如果无法链接则尝试启动 Supervisord 进程
	if err := client.ensureConnected(); err != nil {
		return nil, err
	}
	return client, nil
}

func (c *Client) ensureConnected() error {
	var err error
	for i := 0; i < 3; i++ {
		c.rpcClient, err = xmlrpc.NewClient(c.config.RPCAddress, nil)
		var state State
		if err == nil {
			// 验证连接是否正常
			if state, err = c.GetState(); err == nil {
				fmt.Printf("Connected to Supervisord (state: %s)", state.Name)
				return nil
			}
			// 如果状态不是运行中则尝试重启
			fmt.Printf("Supervisord is not running (state: %s)", state.Name)
			if err = c.Restart(); err == nil {
				continue
			}
		}

		// 如果连接失败则尝试启动
		fmt.Printf("Attempting to start supervisord")
		if err = c.startSupervisord(); err != nil {
			fmt.Printf("Start supervisord failed: %v", err)
		}
		time.Sleep(1 * time.Second)
	}
	return errors.New("connect to supervisord")
}

func (c *Client) startSupervisord() error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "supervisord", "-c", c.config.ConfigPath)
	if err := cmd.Run(); err != nil {
		return errors.Wrap(err, "start supervisord")
	}
	return nil
}

func (c *Client) CallMethodAndVerifyBool(method string, args ...interface{}) error {
	var result bool
	err := c.rpcClient.Call(method, args, &result)
	if err != nil {
		return errors.Wrapf(err, "supervisord call method %s failed", method)
	}

	// 若返回值为 false 则返回错误
	if !result {
		return errors.New("supervisord return false")
	}
	return nil
}
