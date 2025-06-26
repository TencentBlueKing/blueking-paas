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

package ingress

import (
	"fmt"
	"strings"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
)

// ErrDomainGroupSourceType indicates an invalid source type
var ErrDomainGroupSourceType = errors.New("Domain group source type is invalid")

// Default service configuration for Ingress resource, may allow further
// customization in future versions.
const (
	DefaultServiceProcName      = "web"
	DefaultServicePortName      = "http"
	ServerSnippetAnnoKey        = "nginx.ingress.kubernetes.io/server-snippet"
	BackendProtocolAnnoKey      = "nginx.ingress.kubernetes.io/backend-protocol"
	ConfigurationSnippetAnnoKey = "nginx.ingress.kubernetes.io/configuration-snippet"
	RewriteTargetAnnoKey        = "nginx.ingress.kubernetes.io/rewrite-target"
	SSLRedirectAnnoKey          = "nginx.ingress.kubernetes.io/ssl-redirect"
	// SkipFilterCLBAnnoKey 由于 tke 集群默认会为没有绑定 CLB 的 Ingress 创建并绑定公网 CLB 的危险行为，
	// bcs-webhook 会对下发/更新配置时没有指定 clb 的 Ingress 进行拦截，在关闭 tke 集群的 l7-lb-controller 组件后
	// 可以在下发 Ingress 时候添加注解 bkbcs.tencent.com/skip-filter-clb: "true" 以跳过 bcs-webhook 的拦截
	// l7-lb-controller 状态查询：kubectl get deploy l7-lb-controller -n kube-system
	SkipFilterCLBAnnoKey = "bkbcs.tencent.com/skip-filter-clb"
)

// DomainSourceType is the source type for domain groups
type DomainSourceType string

const (
	// DomainSubDomain means domain was allocated by platform, apps are
	// distinguished by sub-domains
	DomainSubDomain DomainSourceType = "subdomain"

	// DomainSubPath means domain was allocated by platform, apps are
	// distinguished by sub-paths, share a single root domain.
	DomainSubPath DomainSourceType = "subpath"

	// DomainCustom means domain was created by user
	DomainCustom DomainSourceType = "custom"
)

// Domain is a simple struct for storing domain
type Domain struct {
	Name           string   `json:"name"`
	Host           string   `json:"host"`
	PathPrefixList []string `json:"pathPrefixList"`

	// The name of Secret resource which contains TLS cert files, empty value
	// means no HTTPS is supported.
	//
	// Currently, the secret resource was created by "apiserver" service. This
	// behaviour may change in the future.
	TLSSecretName string `json:"tlsSecretName"`
}

// GetURLs generates and returns a list of URLs by current value
func (d Domain) GetURLs() []string {
	var scheme string
	if d.TLSSecretName == "" {
		scheme = "http"
	} else {
		scheme = "https"
	}

	var results []string
	for _, p := range d.PathPrefixList {
		// Make sure path starts with "/"
		p = "/" + strings.TrimLeft(p, "/")
		// Make sure path ends with "/"
		if p != "" && !strings.HasSuffix(p, "/") {
			p = p + "/"
		}
		results = append(results, fmt.Sprintf("%s://%s%s", scheme, d.Host, p))
	}
	return results
}

// DomainGroup is a group of domains for accessing Application via HTTP(S)
type DomainGroup struct {
	SourceType DomainSourceType
	Domains    []Domain
}

// MappingToDomainGroups returns all DomainGroups in a mapping object
func MappingToDomainGroups(dgmapping *paasv1alpha1.DomainGroupMapping) []DomainGroup {
	domains := []DomainGroup{}
	for _, domainGroupSpec := range dgmapping.Spec.Data {
		domains = append(domains, TransformDomainGroup(domainGroupSpec))
	}
	return domains
}

// TransformDomainGroup turns the DomainGroup data in specs into DomainGroup
// objects. When multiple apiVersion is adopted in the future, this function may
// become more complicated.
func TransformDomainGroup(dg paasv1alpha1.DomainGroup) DomainGroup {
	domains := lo.Map(dg.Domains, func(d paasv1alpha1.Domain, _ int) Domain {
		return Domain{Host: d.Host, PathPrefixList: d.PathPrefixList, TLSSecretName: d.TLSSecretName, Name: d.Name}
	})
	return DomainGroup{
		SourceType: DomainSourceType(dg.SourceType),
		Domains:    domains,
	}
}

// IngressBuilder is an interface type which build Ingress objects
type IngressBuilder interface {
	Build([]Domain) ([]*networkingv1.Ingress, error)
}

// NewIngressBuilder creates an IngressBuilder object which is capable of creating
// Ingress Resources.
// - bkapp is the BkApp resource which the dgmapping resource reference to.
func NewIngressBuilder(
	sourceType DomainSourceType,
	bkapp *paasv1alpha2.BkApp,
) (IngressBuilder, error) {
	switch sourceType {
	case DomainSubDomain, DomainSubPath:
		return MonoIngressBuilder{bkapp: bkapp, sourceType: sourceType}, nil
	case DomainCustom:
		return CustomIngressBuilder{bkapp: bkapp}, nil
	default:
		return nil, errors.Wrap(ErrDomainGroupSourceType, string(sourceType))
	}
}

// MonoIngressBuilder build Ingress resources for "subdomain" and "subpath" source types
type MonoIngressBuilder struct {
	bkapp      *paasv1alpha2.BkApp
	sourceType DomainSourceType
}

// Build Ingress object, return only one Ingress resource object event when there
// are multiple domains.
func (builder MonoIngressBuilder) Build(domains []Domain) ([]*networkingv1.Ingress, error) {
	bkapp := builder.bkapp

	// TODO: The resource name might conflict if multiple DomainGroupMappings uses
	// same sourceTypes.
	name := fmt.Sprintf("%s-%s", bkapp.Name, builder.sourceType)
	ingress := networkingv1.Ingress{
		TypeMeta: metav1.TypeMeta{APIVersion: "v1", Kind: "Ingress"},
		ObjectMeta: metav1.ObjectMeta{
			Name:        name,
			Namespace:   bkapp.Namespace,
			Labels:      labels.AppDefault(bkapp),
			Annotations: makeAnnotations(bkapp, domains),
		},
		Spec: networkingv1.IngressSpec{
			Rules: makeRules(builder.bkapp, domains),
			TLS:   makeTLS(domains),
		},
	}

	results := []*networkingv1.Ingress{&ingress}
	return results, nil
}

// CustomIngressBuilder build Ingress resources for "custom" source type
type CustomIngressBuilder struct {
	bkapp *paasv1alpha2.BkApp
}

// Build Ingress object, may return multiple Ingress objects when there are more
// than 1 domains.
func (builder CustomIngressBuilder) Build(domains []Domain) ([]*networkingv1.Ingress, error) {
	bkapp := builder.bkapp

	results := []*networkingv1.Ingress{}
	for _, d := range domains {
		name := fmt.Sprintf("custom-%s-%s", bkapp.Name, d.Host)
		// Put Domain.Name in resource name to avoid conflicts when multiple
		// domains have same hostname.
		if d.Name != "" {
			name += ("-" + d.Name)
		}

		annotations := makeAnnotations(bkapp, domains)
		if ingClassName := config.Global.GetCustomDomainIngressClassName(); ingClassName != "" {
			annotations[paasv1alpha2.IngressClassAnnoKey] = ingClassName
		}

		val := networkingv1.Ingress{
			TypeMeta: metav1.TypeMeta{APIVersion: "v1", Kind: "Ingress"},
			ObjectMeta: metav1.ObjectMeta{
				Name:        name,
				Namespace:   bkapp.Namespace,
				Labels:      labels.AppDefault(bkapp),
				Annotations: annotations,
			},
			Spec: networkingv1.IngressSpec{
				Rules: makeRules(builder.bkapp, []Domain{d}),
				TLS:   makeTLS([]Domain{d}),
			},
		}

		results = append(results, &val)

	}
	return results, nil
}

// Make rule objects
func makeRules(bkapp *paasv1alpha2.BkApp, domains []Domain) []networkingv1.IngressRule {
	rules := make([]networkingv1.IngressRule, 0)
	for _, d := range domains {
		r := networkingv1.IngressRule{
			Host: d.Host,
			IngressRuleValue: networkingv1.IngressRuleValue{
				HTTP: &networkingv1.HTTPIngressRuleValue{
					Paths: makePaths(bkapp, d.PathPrefixList),
				},
			},
		}
		rules = append(rules, r)
	}
	return rules
}

// Make TLS field values
func makeTLS(domains []Domain) (results []networkingv1.IngressTLS) {
	// Group hosts by secret name
	secretMap := make(map[string][]string)
	for _, d := range domains {
		if n := d.TLSSecretName; n != "" {
			secretMap[n] = append(secretMap[n], d.Host)
		}
	}

	for sec, hosts := range secretMap {
		results = append(results, networkingv1.IngressTLS{Hosts: hosts, SecretName: sec})
	}
	return results
}

// Make path objects
func makePaths(bkapp *paasv1alpha2.BkApp, pathPrefixes []string) []networkingv1.HTTPIngressPath {
	results := make([]networkingv1.HTTPIngressPath, 0)

	isGRPC := isBackendProtocolGRPC(bkapp)

	var path string
	for _, prefix := range pathPrefixes {
		// gRPC protocol. Field Path is set to "/"
		if isGRPC {
			path = "/"
		} else {
			path = makeLocationPath(prefix)
		}
		ingressPath := networkingv1.HTTPIngressPath{
			Path:     path,
			PathType: lo.ToPtr(networkingv1.PathTypeImplementationSpecific),
			Backend:  *makeIngressServiceBackend(bkapp),
		}
		results = append(results, ingressPath)
	}
	return results
}

// makeIngressServiceBackend return the ingress backend related to the process service with exposed type bk/http,
// otherwise return the default one.
func makeIngressServiceBackend(bkapp *paasv1alpha2.BkApp) *networkingv1.IngressBackend {
	if bkapp.HasProcServices() {
		if backend := makeIngressBackendByProcService(bkapp); backend != nil {
			return backend
		}
	}

	return makeDefaultIngressBackend(bkapp)
}

// makeIngressBackendByProcService return the ingress backend by the process service with exposed type bk/http,
// otherwise return nil.
func makeIngressBackendByProcService(bkapp *paasv1alpha2.BkApp) *networkingv1.IngressBackend {
	exposedProcService := bkapp.FindExposedProcService()

	if exposedProcService == nil {
		return nil
	}

	return &networkingv1.IngressBackend{
		Service: &networkingv1.IngressServiceBackend{
			Name: names.Service(bkapp, exposedProcService.ProcName),
			Port: networkingv1.ServiceBackendPort{
				Name: exposedProcService.ProcSvc.Name,
			},
		},
	}
}

// makeDefaultIngressBackend return the default ingress backend for the bkapp which not enable proc services feature
func makeDefaultIngressBackend(bkapp *paasv1alpha2.BkApp) *networkingv1.IngressBackend {
	return &networkingv1.IngressBackend{
		Service: &networkingv1.IngressServiceBackend{
			Name: names.Service(bkapp, DefaultServiceProcName),
			Port: networkingv1.ServiceBackendPort{
				Name: DefaultServicePortName,
			},
		},
	}
}

// RegexLocationBuilder provide a generic location path which will rewrite request path to root
//
// For builtin sub-domain request will result in the following rewrites:
// - "{app-code}.example.com" rewrites to "{app-code}.sub-domain.example.com/"
// - "{app-code}.example.com/" rewrites to "{app-code}.sub-domain.example.com/"
// - "{app-code}.example.com/foo" rewrites to "{app-code}.sub-domain.example.com/foo"
//
// For builtin sub-path request will result in the following rewrites:
// - "example.com/{app-code}" will rewrites to "example.com/"
// - "example.com/{app-code}/" will rewrites to "example.com/"
// - "example.com/{app-code}/foo" will rewrites to "example.com/foo"
//
// For custom domain which path is "/", will result in the following rewrites:
// - "custom-domain.com/" rewrites to "custom-domain.com/"
// - "custom-domain.com/foo" rewrites to "custom-domain.com/foo"
//
// For custom domain which path is "example/", will result in the following rewrites:
// - "custom-domain.com/example/" rewrites to "custom-domain.com/"
// - "custom-domain.com/example/foo" rewrites to "custom-domain.com/foo"
type RegexLocationBuilder struct{}

// makeLocationPath return a regex path, which should work well with `rewrite-target`
// In this function, we guarantee that:
// 1. "/$2" is the user request path to the app (without any sub-path provided from platform or custom domain)
// 2. "/$1$3" is the sub-path provided from platform or custom domain, for root path case, it should be root path "/"
// 3. "/$1$3/$2" is the real request path to the ingress
func (b *RegexLocationBuilder) makeLocationPath(path string) string {
	if path == "/" {
		// for root path, we don't need any rewrite at all, but for compatible with sub-path case
		// we return the regex as below.
		// Examples:
		// - request path = "/"
		// "/$2" = "/", "/$1$3" = "/"
		// - request path = "/foo"
		// "/$2" = "/foo", "/$1$3" = "/"
		return "/()(.*)"
	}
	trimPath := strings.TrimLeft(path, "/")
	// use regex to rewrite request path to root, we can get sub-path from "/$1$3"
	// Examples:
	// - path = "/sub-path/", request path = "/sub-path/foo"
	// $1 = "sub-path", $2 = "foo", $3 = "", "/$1$3" = "/sub-path"
	// - path = "/sub-path", request path = "/sub-path/foo"
	// $1 = "sub-path", $2 = "foo", $3 = nil, "/$1$3" = "/sub-path"
	// - path = "/sub-path", request path ="/sub-path"
	// $1 = nil, $2 = nil, $3 = "sub-path, "/$1$3" = "/sub-path"
	// - path = "/a/b/c/d/", request path = "/a/b/c/d/e/f"
	// $1 = "/a/b/c/d", $2 = "e/f", $3 = "", "/$1$3" = "/a/b/c/d
	if strings.HasSuffix(trimPath, "/") {
		// for the case trimPath ends with "/"
		return fmt.Sprintf("/(%s)/(.*)()", strings.TrimRight(trimPath, "/"))
	} else {
		// adapter the trimPath that ends without slash
		return fmt.Sprintf("/(%s)/(.*)|/(%s$)", trimPath, trimPath)
	}
}

func (b *RegexLocationBuilder) makeRewriteTarget() string {
	// "/$2" is the user request path to the app (without any sub-path provided from platform or custom domain)
	// See also: the guarantee of makeLocationPath
	return "/$2"
}

// MakeConfigurationSnippet return a configuration snippet
func (b *RegexLocationBuilder) MakeConfigurationSnippet(bkapp *paasv1alpha2.BkApp, domains []Domain) string {
	if len(domains) == 0 {
		return ""
	}
	// "/$1$3" is the sub-path provided from platform or custom domain, for root path case, it should be root path "/"
	// See also: the guarantee of makeLocationPath
	return "proxy_set_header X-Script-Name /$1$3;"
}

// MakeServerSnippet RegexLocationBuilder 不提供 server snippet
func (b *RegexLocationBuilder) MakeServerSnippet(bkapp *paasv1alpha2.BkApp, domains []Domain) string {
	return ""
}

// make server snippet, this method will call all registered plugins
func makeServerSnippet(bkapp *paasv1alpha2.BkApp, domains []Domain) string {
	return strings.Join(lo.Map(registeredIngressPlugins, func(plugin NginxIngressPlugin, i int) string {
		return plugin.MakeServerSnippet(bkapp, domains)
	}), "\n")
}

// make configuration snippet, this method will call all registered plugins
func makeConfigurationSnippet(bkapp *paasv1alpha2.BkApp, domains []Domain) string {
	return strings.Join(lo.Map(registeredIngressPlugins, func(plugin NginxIngressPlugin, i int) string {
		return plugin.MakeConfigurationSnippet(bkapp, domains)
	}), "\n")
}

// makeLocationPath is a shortcut for RegexLocationBuilder.makeLocationPath
func makeLocationPath(path string) string {
	return (&RegexLocationBuilder{}).makeLocationPath(path)
}

// makeRewriteTarget is a shortcut for RegexLocationBuilder.makeRewriteTarget
func makeRewriteTarget() string {
	return (&RegexLocationBuilder{}).makeRewriteTarget()
}

// makeAnnotations return a map of annotations
func makeAnnotations(bkapp *paasv1alpha2.BkApp, domains []Domain) map[string]string {
	annotations := map[string]string{SkipFilterCLBAnnoKey: "true"}

	if isBackendProtocolGRPC(bkapp) {
		// TODO: 支持相关插件的 ServerSnippetAnnoKey 和 ConfigurationSnippetAnnoKey. 目前验证了 accessControl 插件不能直接使用
		annotations[SSLRedirectAnnoKey] = "true"
		annotations[BackendProtocolAnnoKey] = "GRPC"
	} else {
		annotations[RewriteTargetAnnoKey] = makeRewriteTarget()
		annotations[ServerSnippetAnnoKey] = makeServerSnippet(bkapp, domains)
		annotations[ConfigurationSnippetAnnoKey] = makeConfigurationSnippet(bkapp, domains)
	}

	// 如果已配置 ingressClassName，则使用
	if ingClassName := config.Global.GetIngressClassName(); ingClassName != "" {
		// WARNING: kubernetes.io/ingress.class annotation will be deprecated in the future.
		// See https://kubernetes.github.io/ingress-nginx/user-guide/multiple-ingress/#multiple-ingress-controllers
		annotations[paasv1alpha2.IngressClassAnnoKey] = ingClassName
	}

	return annotations
}

func isBackendProtocolGRPC(bkapp *paasv1alpha2.BkApp) bool {
	exposedProcService := bkapp.FindExposedProcService()
	if exposedProcService != nil && exposedProcService.ExposedTypeName == paasv1alpha2.ExposedTypeNameBkGRPC {
		return true
	}
	return false
}

func init() {
	RegistryPlugin(&RegexLocationBuilder{})
}
