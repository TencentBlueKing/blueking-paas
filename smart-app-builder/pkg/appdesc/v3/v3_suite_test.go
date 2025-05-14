package v3_test

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestV3(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "V3 Suite")
}
