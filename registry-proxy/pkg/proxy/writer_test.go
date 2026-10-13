package proxy

import (
	"net/url"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("sameEndpoint", func() {
	DescribeTable("compares scheme, host and port with default ports filled in",
		func(upstream, loc string, want bool) {
			u, _ := url.Parse(upstream)
			l, _ := url.Parse(loc)
			Expect(sameEndpoint(l, u)).To(Equal(want))
		},
		Entry("identical", "https://registry.example.com", "https://registry.example.com/v2/", true),
		Entry("explicit 443", "https://registry.example.com", "https://registry.example.com:443/v2/", true),
		Entry("upstream with explicit 443", "https://registry.example.com:443", "https://registry.example.com/v2/", true),
		Entry("explicit 80", "http://registry.local", "http://registry.local:80/v2/", true),
		Entry("host case", "https://registry.example.com", "https://Registry.Example.COM/v2/", true),
		Entry("other port", "https://registry.example.com", "https://registry.example.com:8443/v2/", false),
		Entry("other scheme", "https://registry.example.com", "http://registry.example.com/v2/", false),
		Entry("https on port 80", "http://registry.local", "https://registry.local:80/v2/", false),
		Entry("other host", "https://registry.example.com", "https://storage.example.com/v2/", false),
	)
})

var _ = Describe("rewriteLink", func() {
	up, _ := url.Parse("https://registry.example.com")

	DescribeTable("rewrites links to the upstream /v2/ into proxy-relative links",
		func(link, want string) {
			Expect(rewriteLink(link, up, "alias/")).To(Equal(want))
		},
		Entry("relative", `</v2/a/tags/list?n=1>; rel="next"`, `</v2/alias/a/tags/list?n=1>; rel="next"`),
		Entry("explicit 443", `<https://registry.example.com:443/v2/a/tags/list?n=1>; rel="next"`,
			`</v2/alias/a/tags/list?n=1>; rel="next"`),
		Entry("foreign host", `<https://other.example.com/v2/a/tags/list>; rel="next"`,
			`<https://other.example.com/v2/a/tags/list>; rel="next"`),
	)
})
