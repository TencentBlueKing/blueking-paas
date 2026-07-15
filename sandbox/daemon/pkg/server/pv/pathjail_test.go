package pv

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Resolve", func() {
	var cfsRoot string
	const basePath = "app/volume1"

	BeforeEach(func() {
		var err error
		cfsRoot, err = os.MkdirTemp("", "jail-test-*")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		if cfsRoot != "" {
			os.RemoveAll(cfsRoot) // nolint
		}
	})

	It("resolves a normal relative path within the jail", func() {
		full, jailRoot, err := Resolve(cfsRoot, basePath, "outputs/report.html")
		Expect(err).NotTo(HaveOccurred())
		Expect(jailRoot).To(Equal(filepath.Join(cfsRoot, basePath)))
		Expect(full).To(Equal(filepath.Join(cfsRoot, basePath, "outputs/report.html")))
	})

	It("resolves the jail root itself when rel_path is empty", func() {
		full, jailRoot, err := Resolve(cfsRoot, basePath, "")
		Expect(err).NotTo(HaveOccurred())
		Expect(full).To(Equal(jailRoot))
	})

	It("rejects ../ traversal", func() {
		_, _, err := Resolve(cfsRoot, basePath, "../../etc/passwd")
		Expect(err).To(MatchError(ErrPathEscape))
	})

	It("neutralizes a leading-slash rel_path into the jail", func() {
		// filepath.Join strips the leading slash, so an "absolute" rel_path
		// is contained within the jail rather than escaping it.
		full, jailRoot, err := Resolve(cfsRoot, basePath, "/etc/passwd")
		Expect(err).NotTo(HaveOccurred())
		Expect(full).To(Equal(filepath.Join(jailRoot, "etc/passwd")))
	})

	It("rejects a sneaky prefix sibling (jailRoot-evil)", func() {
		// Join cleans this to cfsRoot/app, escaping cfsRoot/app/volume1
		_, _, err := Resolve(cfsRoot, basePath, "../volume1-evil/secret")
		Expect(err).To(MatchError(ErrPathEscape))
	})
})

var _ = Describe("ResolveSymlink", func() {
	var (
		cfsRoot  string
		jailRoot string
	)
	const basePath = "app/volume1"

	BeforeEach(func() {
		var err error
		cfsRoot, err = os.MkdirTemp("", "jail-symlink-*")
		Expect(err).NotTo(HaveOccurred())
		jailRoot = filepath.Join(cfsRoot, basePath)
		Expect(os.MkdirAll(jailRoot, 0o755)).To(Succeed())
	})

	AfterEach(func() {
		if cfsRoot != "" {
			os.RemoveAll(cfsRoot) // nolint
		}
	})

	It("resolves a real file inside the jail", func() {
		target := filepath.Join(jailRoot, "file.txt")
		Expect(os.WriteFile(target, []byte("hi"), 0o644)).To(Succeed())

		real, err := ResolveSymlink(target, jailRoot)
		Expect(err).NotTo(HaveOccurred())
		Expect(real).To(Equal(target))
	})

	It("rejects a symlink pointing outside the jail", func() {
		// A file outside the jail, and a symlink inside pointing to it
		outside := filepath.Join(cfsRoot, "outside.txt")
		Expect(os.WriteFile(outside, []byte("secret"), 0o644)).To(Succeed())

		link := filepath.Join(jailRoot, "escape")
		Expect(os.Symlink(outside, link)).To(Succeed())

		_, err := ResolveSymlink(link, jailRoot)
		Expect(err).To(MatchError(ErrPathEscape))
	})

	It("returns a not-exist error for a missing path", func() {
		_, err := ResolveSymlink(filepath.Join(jailRoot, "nope"), jailRoot)
		Expect(os.IsNotExist(err)).To(BeTrue())
	})
})
