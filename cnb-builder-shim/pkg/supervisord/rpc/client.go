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
	"github.com/kolo/xmlrpc"
	"github.com/pkg/errors"
)

// Client 是 supervisord 客户端
type Client struct {
	rpcClient *xmlrpc.Client
	config    ClientConfig
}

// ClientConfig 客户端配置
type ClientConfig struct {
	RPCAddress string // XML-RPC 地址
}

// NewClient 新建 RPC 客户端
func NewClient(rpcAddress string) *Client {
	return &Client{config: ClientConfig{RPCAddress: rpcAddress}}
}

// 请求 rpc 方法接口并验证 bool 类型返回
func (c *Client) callMethodWithCheck(method string, args ...interface{}) error {
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
