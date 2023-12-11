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
package dockercreds

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/name"
	"github.com/google/go-containerregistry/pkg/v1/remote"
	"github.com/google/go-containerregistry/pkg/v1/remote/transport"
	"github.com/pkg/errors"
)

// VerifyWriteAccess verifies write access to a container image with the given reference(tag or digest hash).
// return an error if the keychain does not have write access to the image.
func VerifyWriteAccess(keychain authn.Keychain, reference string) error {
	ref, err := name.ParseReference(reference, name.WeakValidation)
	if err != nil {
		return errors.Wrapf(err, "Error parsing reference %q", reference)
	}

	if err = remote.CheckPushPermission(ref, keychain, http.DefaultTransport); err != nil {
		return diagnoseIfTransportError(err)
	}

	return nil
}

// VerifyReadAccess verifies read access to a container image with the given reference(tag or digest hash).
// return an error if the user does not have read access to the image.
func VerifyReadAccess(keychain authn.Keychain, reference string) error {
	ref, err := name.ParseReference(reference, name.WeakValidation)
	if err != nil {
		return errors.Wrapf(err, "Error parsing reference %q", reference)
	}

	if _, err = remote.Get(ref, remote.WithAuthFromKeychain(keychain), remote.WithTransport(http.DefaultTransport)); err != nil {
		return diagnoseIfTransportError(err)
	}

	return nil
}

func diagnoseIfTransportError(err error) error {
	if err == nil {
		return nil
	}

	// transport.Error implements error to support the following error specification:
	// https://github.com/docker/distribution/blob/master/docs/spec/api.md#errors
	transportError, ok := err.(*transport.Error)
	if !ok {
		return err
	}

	// handle artifactory. refer test case
	if transportError.StatusCode == 401 {
		return errors.New(string(transport.UnauthorizedErrorCode))
	}

	if len(transportError.Errors) == 0 {
		return err
	}

	var messageBuilder strings.Builder
	for _, diagnosticError := range transportError.Errors {
		messageBuilder.WriteString(fmt.Sprintf("%s. ", diagnosticError.Message))
	}

	return errors.New(messageBuilder.String())
}
