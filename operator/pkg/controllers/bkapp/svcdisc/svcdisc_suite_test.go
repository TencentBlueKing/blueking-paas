package svcdisc_test

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestSvcdisc(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Svcdisc Suite")
}
