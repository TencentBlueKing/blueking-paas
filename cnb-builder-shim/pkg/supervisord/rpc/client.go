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
package rpc

import (
	"fmt"
	"github.com/kolo/xmlrpc"
	"github.com/pkg/errors"
	"time"
)

type Client struct {
	rpcClient *xmlrpc.Client
	config    ClientConfig
}

type ClientConfig struct {
	RPCAddress string // XML-RPC 地址
}

// NewClient 新建 RPC 客户端
func NewClient(rpcAddress string) (*Client, error) {
	client := &Client{config: ClientConfig{RPCAddress: rpcAddress}}

	var err error
	for attempt := 0; attempt < 3; attempt++ {
		var state State
		client.rpcClient, err = xmlrpc.NewClient(rpcAddress, nil)
		if err == nil {
			// 验证连接是否正常
			if state, err = client.GetState(); err == nil {
				fmt.Printf("Connected to Supervisord (state: %s)", state.Name)
			}
			// 如果获取状态失败或者状态不是运行中则尝试重启
			if err == nil || state.Name != StateNameRunning {
				if err = client.Restart(); err == nil {
					fmt.Println("Supervisord restarted")
					time.Sleep(1 * time.Second)
					continue
				}
			} else {
				return client, nil
			}
		}
	}
	return client, errors.Wrap(err, "new supervisord client")
}

// AutoConnectClient 自动连接到 Supervisord,若 Supervisord 未启动则尝试启动
func AutoConnectClient(rpcAddress string, configPath string) (*Client, error) {
	var err error
	for attempt := 0; attempt < 3; attempt++ {
		client, err := NewClient(rpcAddress)
		if err == nil {
			return client, nil
		}
		server := NewServer(configPath)
		if err = server.Start(); err != nil {
			fmt.Println("Failed to start supervisord server", err)
		}
		// 等待服务就绪
		time.Sleep(2 * time.Second)
	}
	return nil, err
}

// 请求 rpc 方法接口并验证 bool 类型返回
func (c *Client) callMethodAndVerifyBool(method string, args ...interface{}) error {
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
