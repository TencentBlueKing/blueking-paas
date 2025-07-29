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

package config

// FetchMethod 源码获取方式
type FetchMethod string

const (
	HTTP   FetchMethod = "HTTP"
	BkRepo FetchMethod = "BK_REPO"
	GIT    FetchMethod = "GIT"
)

// SourceCodeConfig 源码配置
type SourceCodeConfig struct {
	// 源码获取方式
	FetchMethod FetchMethod
	// 源码地址
	FetchUrl string
	// Git 仓库版本
	GitRevision string
	// 工作目录
	Workspace string
}

// CORSConfig 跨域配置
type CORSConfig struct {
	// 允许的来源
	AllowOrigins []string
	// 允许的 HTTP 方法
	AllowMethods []string
	// 允许的请求头
	AllowHeaders []string
	// 暴露的响应头
	ExposeHeaders []string
	// 凭证共享
	AllowCredentials bool
}

// ServiceConfig 服务配置
type ServiceConfig struct {
	// 跨域配置
	CORS CORSConfig
}

// Config  全局配置
type Config struct {
	// 源码配置
	SourceCode SourceCodeConfig
	// 服务配置
	Service ServiceConfig
	// 模块配置
	ModuleName string
}
