package main_test

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestDevInit(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "DevInit Suite")
}
