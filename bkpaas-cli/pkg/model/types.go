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

package model

const (
	// AppTypeDefault 普通应用
	AppTypeDefault = "default"

	// AppTypeCNative 云原生应用
	AppTypeCNative = "cloud_native"
)

const (
	// DeployStatusSuccessful 部署成功（仅普通应用）
	DeployStatusSuccessful = "successful"
	// DeployStatusFailed 部署失败（仅普通应用）
	DeployStatusFailed = "failed"
	// DeployStatusInterrupted 部署中断（仅普通应用）
	DeployStatusInterrupted = "interrupted"
	// DeployStatusPending 等待部署完成（共用）
	DeployStatusPending = "pending"
	// DeployStatusPending 部署进行中（仅云原生应用）
	DeployStatusProgressing = "progressing"
	// DeployStatusReady 已就绪（仅云原生应用）
	DeployStatusReady = "ready"
	// DeployStatusError 未知状态（仅云原生应用）
	DeployStatusError = "error"
	// DeployStatusUnknown 未知状态（仅云原生应用）
	DeployStatusUnknown = "unknown"
)

// AppInfo 应用信息接口
type AppInfo interface {
	// String 将应用信息转换成可打印展示的字符串
	String() string
}

// DeployResult 部署结果接口
type DeployResult interface {
	// IsStable 根据部署结果，判断是否到达稳定状态（如：成功/失败/已中断）
	IsStable() bool
	// String 将部署结果转换成可打印展示的字符串
	String() string
}

// DeployHistory 部署历史接口
type DeployHistory interface {
	// Length 返回部署历史总数量
	Length() int
	// Latest 获取最新一次的部署结果
	Latest() *AppDeployRecord
	// String 将部署结果转换成可打印展示的字符串
	String() string
}
