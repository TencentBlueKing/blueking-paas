package httputil

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestHttputil(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Httputil Suite")
}
