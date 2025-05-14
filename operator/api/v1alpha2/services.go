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

package v1alpha2

import (
	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
)

// ExposedTypeName defines the exposed type of the service
// +enum
type ExposedTypeName string

const (
	// ExposedTypeNameBkHttp is the exposed type which implements based on DomainGroupMapping
	ExposedTypeNameBkHttp ExposedTypeName = "bk/http"
)

// ProcService is a process service which used to expose network
type ProcService struct {
	// The name of the service.
	Name string `json:"name"`

	// Number of the port to access on the pods(container) targeted by the service.
	TargetPort int32 `json:"targetPort"`

	// The protocol of the service. Default value is TCP if not specified.
	// +optional
	Protocol corev1.Protocol `json:"protocol,omitempty"`

	// The exposed type of the service. If not specified(or specified as null), the service can only be accessed
	// within the cluster, not from outside. however, it is primarily informational here,
	// the real control logic is in paas "apiserver".
	// TODO implement control logic in operator?
	//
	// ExposedType can be one of the following:
	// - {Name: ExposedTypeNameBkHttp} exposed by DomainGroupMapping
	//
	// +optional
	ExposedType *ExposedType `json:"exposedType,omitempty"`

	// The port that will be exposed by this service. If this is not specified, the value of
	// the 'targetPort' field is used.
	// +optional
	Port int32 `json:"port,omitempty"`
}

// ExposedType is the exposed type of the service
type ExposedType struct {
	// The name of the exposed type.
	Name ExposedTypeName `json:"name"`
}

func validateExposedType(t *ExposedType) error {
	if t != nil && t.Name != ExposedTypeNameBkHttp {
		return errors.New("unsupported exposed type")
	}
	return nil
}

func validateServiceProtocol(protocol corev1.Protocol) error {
	switch protocol {
	case corev1.ProtocolTCP, corev1.ProtocolUDP:
		return nil
	default:
		return errors.New("unsupported protocol")
	}
}
