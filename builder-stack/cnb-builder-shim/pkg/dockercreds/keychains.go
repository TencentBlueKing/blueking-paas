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
	"encoding/json"
	"os"
	"regexp"

	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/pkg/errors"
)

// EnvRegistryAuth The env aar that store registry credentials
const EnvRegistryAuth = "CNB_REGISTRY_AUTH"

// DefaultKeychain returns a keychain containing authentication configuration for the given images
// from the following sources, if they exist, in order of precedence:
// the provided environment variable
// the docker config.json file
func DefaultKeychain() (authn.Keychain, error) {
	envKeychain, err := NewEnvKeychain(EnvRegistryAuth)
	if err != nil {
		return authn.DefaultKeychain, err
	}
	return authn.NewMultiKeychain(
		envKeychain,
		authn.DefaultKeychain,
	), nil
}

// NewEnvKeychain returns an authn.Keychain that uses the provided environment variable as a source of credentials.
// The value of the environment variable should be a JSON object that maps OCI registry hostnames to Authorization headers.
func NewEnvKeychain(envVarName string) (authn.Keychain, error) {
	authHeaders, err := ReadEnvVar(envVarName)
	if err != nil {
		return nil, errors.Wrap(err, "reading auth env var")
	}
	return &EnvKeychain{AuthHeaders: authHeaders}, nil
}

// EnvKeychain is an implementation of authn.Keychain that stores credentials as auth headers.
type EnvKeychain struct {
	AuthHeaders map[string]string
}

// Resolve resource by EnvKeychain, if any source matched, return the Authenticator, otherwise, return Anonymous user.
func (k *EnvKeychain) Resolve(resource authn.Resource) (authn.Authenticator, error) {
	for _, key := range []string{
		resource.String(),
		resource.RegistryStr(),
	} {
		header, ok := k.AuthHeaders[key]
		if ok {
			authConfig, err := authHeaderToConfig(header)
			if err != nil {
				return nil, errors.Wrap(err, "parsing auth header")
			}
			return authn.FromConfig(*authConfig), nil
		}
	}
	return authn.Anonymous, nil
}

var (
	basicAuthRegExp     = regexp.MustCompile("(?i)^basic (.*)$")
	bearerAuthRegExp    = regexp.MustCompile("(?i)^bearer (.*)$")
	identityTokenRegExp = regexp.MustCompile("(?i)^x-identity (.*)$")
)

func authHeaderToConfig(header string) (*authn.AuthConfig, error) {
	if matches := basicAuthRegExp.FindAllStringSubmatch(header, -1); len(matches) != 0 {
		return &authn.AuthConfig{
			Auth: matches[0][1],
		}, nil
	}

	if matches := bearerAuthRegExp.FindAllStringSubmatch(header, -1); len(matches) != 0 {
		return &authn.AuthConfig{
			RegistryToken: matches[0][1],
		}, nil
	}

	if matches := identityTokenRegExp.FindAllStringSubmatch(header, -1); len(matches) != 0 {
		return &authn.AuthConfig{
			IdentityToken: matches[0][1],
		}, nil
	}

	return nil, errors.New("unknown auth type from header")
}

// ReadEnvVar parses an environment variable to produce a map of 'registry url' to 'authorization header'.
//
// Complementary to `BuildEnvVar`.
//
// Example Input:
//
//	{"gcr.io": "Bearer asdf=", "docker.io": "Basic qwerty="}
//
// Example Output:
//
//	gcr.io -> Bearer asdf=
//	docker.io -> Basic qwerty=
func ReadEnvVar(envVar string) (map[string]string, error) {
	authMap := map[string]string{}

	env := os.Getenv(envVar)
	if env != "" {
		err := json.Unmarshal([]byte(env), &authMap)
		if err != nil {
			return nil, errors.Wrapf(err, "failed to parse %s value", envVar)
		}
	}

	return authMap, nil
}
