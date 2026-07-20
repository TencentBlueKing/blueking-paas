package volumefs

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("volume root", func() {
	var rootDir string

	BeforeEach(func() {
		var err error
		rootDir, err = os.MkdirTemp("", "volume-root-test-*")
		Expect(err).NotTo(HaveOccurred())
		Expect(os.MkdirAll(filepath.Join(rootDir, testBasePath), 0o755)).To(Succeed())
	})

	AfterEach(func() {
		Expect(os.RemoveAll(rootDir)).To(Succeed())
	})

	It("opens the requested volume below the storage root", func() {
		root, err := openVolumeRoot(rootDir, testBasePath)
		Expect(err).NotTo(HaveOccurred())
		defer root.Close() // nolint

		Expect(root.MkdirAll("outputs", 0o755)).To(Succeed())
		file, err := root.OpenFile("outputs/report.html", os.O_CREATE|os.O_WRONLY, 0o644)
		Expect(err).NotTo(HaveOccurred())
		_, err = file.Write([]byte("ok"))
		Expect(err).NotTo(HaveOccurred())
		Expect(file.Close()).To(Succeed())

		file, err = root.Open("outputs/report.html")
		Expect(err).NotTo(HaveOccurred())
		defer file.Close() // nolint
		content, err := io.ReadAll(file)
		Expect(err).NotTo(HaveOccurred())
		Expect(content).To(Equal([]byte("ok")))
	})

	It("rejects lexical path escapes before operating on the root", func() {
		for _, name := range []string{"../../etc/passwd", "../volume-evil/file", "/etc/passwd"} {
			_, err := validateRootPath(name)
			Expect(errors.Is(err, ErrPathEscape)).To(BeTrue(), name)
		}
	})

	It("allows the root directory itself", func() {
		name, err := validateRootPath("")
		Expect(err).NotTo(HaveOccurred())
		Expect(name).To(Equal("."))
	})

	It("rejects a base_path that escapes rootDir", func() {
		for _, basePath := range []string{"../sibling", "/etc", "."} {
			_, err := openVolumeRoot(rootDir, basePath)
			Expect(errors.Is(err, ErrPathEscape)).To(BeTrue(), basePath)
		}
	})

	It("does not follow a base_path symlink outside the storage root", func() {
		outside := filepath.Join(rootDir, "outside")
		Expect(os.MkdirAll(outside, 0o755)).To(Succeed())
		Expect(os.Symlink(outside, filepath.Join(rootDir, "escaped-volume"))).To(Succeed())

		_, err := openVolumeRoot(rootDir, "escaped-volume")
		Expect(err).To(HaveOccurred())
		Expect(strings.Contains(err.Error(), "path escapes")).To(BeTrue())
	})

	It("does not follow a file symlink outside the volume root", func() {
		outside := filepath.Join(rootDir, "secret.txt")
		Expect(os.WriteFile(outside, []byte("secret"), 0o644)).To(Succeed())
		Expect(os.Symlink(outside, filepath.Join(rootDir, testBasePath, "escape"))).To(Succeed())

		root, err := openVolumeRoot(rootDir, testBasePath)
		Expect(err).NotTo(HaveOccurred())
		defer root.Close() // nolint

		_, err = root.Open("escape")
		Expect(err).To(HaveOccurred())
		Expect(strings.Contains(err.Error(), "path escapes")).To(BeTrue())
	})

	It("removes a symlink without dereferencing its target", func() {
		target := filepath.Join(rootDir, testBasePath, "target.txt")
		link := filepath.Join(rootDir, testBasePath, "link.txt")
		Expect(os.WriteFile(target, []byte("x"), 0o644)).To(Succeed())
		Expect(os.Symlink(target, link)).To(Succeed())

		root, err := openVolumeRoot(rootDir, testBasePath)
		Expect(err).NotTo(HaveOccurred())
		defer root.Close() // nolint
		Expect(root.Remove("link.txt")).To(Succeed())

		_, err = os.Lstat(link)
		Expect(os.IsNotExist(err)).To(BeTrue())
		_, err = os.Stat(target)
		Expect(err).NotTo(HaveOccurred())
	})
})
