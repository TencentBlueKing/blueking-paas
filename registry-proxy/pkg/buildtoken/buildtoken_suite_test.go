package buildtoken

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestBuildToken(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "pkg/buildtoken Suite")
}
