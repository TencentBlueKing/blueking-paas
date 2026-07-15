package pv

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestPv(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "PV Suite")
}
