package filediffer_test

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestFileDiffer(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "File Differ Suite")
}
