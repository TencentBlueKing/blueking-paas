package launch_test

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestLaunch(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Launch Suite")
}
