package httputil

import (
	"errors"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("DefaultValidator", func() {
	var validator *DefaultValidator

	BeforeEach(func() {
		validator = &DefaultValidator{}
	})

	Describe("ValidateStruct", func() {
		Context("validate regular struct", func() {
			type SimpleStruct struct {
				Name  string `validate:"required"`
				Email string `validate:"required,email"`
				Age   int    `validate:"gte=0,lte=150"`
			}

			It("should pass validation for valid struct", func() {
				valid := SimpleStruct{
					Name:  "John Doe",
					Email: "john@example.com",
					Age:   30,
				}

				err := validator.ValidateStruct(valid)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should reject struct with missing required field", func() {
				invalid := SimpleStruct{
					Email: "john@example.com",
					Age:   30,
				}

				err := validator.ValidateStruct(invalid)
				Expect(err).To(HaveOccurred())
			})

			It("should reject invalid email", func() {
				invalid := SimpleStruct{
					Name:  "John Doe",
					Email: "invalid-email",
					Age:   30,
				}

				err := validator.ValidateStruct(invalid)
				Expect(err).To(HaveOccurred())
			})

			It("should reject out of range value", func() {
				invalid := SimpleStruct{
					Name:  "John Doe",
					Email: "john@example.com",
					Age:   200,
				}

				err := validator.ValidateStruct(invalid)
				Expect(err).To(HaveOccurred())
			})
		})

		Context("validate pointer type", func() {
			type PointerStruct struct {
				Name string `validate:"required"`
			}

			It("should validate pointer to struct", func() {
				valid := &PointerStruct{
					Name: "Test",
				}

				err := validator.ValidateStruct(valid)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should reject invalid pointer struct", func() {
				invalid := &PointerStruct{}

				err := validator.ValidateStruct(invalid)
				Expect(err).To(HaveOccurred())
			})

			It("should handle nil pointer", func() {
				err := validator.ValidateStruct(nil)
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("validate slice and array", func() {
			type Item struct {
				Name string `validate:"required"`
				ID   int    `validate:"required,gt=0"`
			}

			It("should validate valid slice", func() {
				validSlice := []Item{
					{Name: "Item1", ID: 1},
					{Name: "Item2", ID: 2},
				}

				err := validator.ValidateStruct(validSlice)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should reject slice with invalid elements", func() {
				invalidSlice := []Item{
					{Name: "Item1", ID: 1},
					{Name: "", ID: 2},
					{Name: "Item3", ID: 0},
				}

				err := validator.ValidateStruct(invalidSlice)
				Expect(err).To(HaveOccurred())

				sliceErr, ok := err.(SliceValidationError)
				Expect(ok).To(BeTrue())
				Expect(len(sliceErr)).To(BeNumerically(">", 0))
			})

			It("should pass validation for empty slice", func() {
				emptySlice := []Item{}

				err := validator.ValidateStruct(emptySlice)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should validate array", func() {
				validArray := [2]Item{
					{Name: "Item1", ID: 1},
					{Name: "Item2", ID: 2},
				}

				err := validator.ValidateStruct(validArray)
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("optional tag", func() {
			type OptionalStruct struct {
				Required string  `validate:"required"`
				Optional *string `validate:"optional"`
			}

			It("should allow optional field to be nil", func() {
				valid := OptionalStruct{
					Required: "value",
					Optional: nil,
				}

				err := validator.ValidateStruct(valid)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should allow optional field to have value", func() {
				optValue := "optional value"
				valid := OptionalStruct{
					Required: "value",
					Optional: &optValue,
				}

				err := validator.ValidateStruct(valid)
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("nested struct", func() {
			type Address struct {
				Street string `validate:"required"`
				City   string `validate:"required"`
			}

			type Person struct {
				Name    string  `validate:"required"`
				Address Address `validate:"required"`
			}

			It("should validate nested struct", func() {
				valid := Person{
					Name: "John",
					Address: Address{
						Street: "123 Main St",
						City:   "New York",
					},
				}

				err := validator.ValidateStruct(valid)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should reject invalid field in nested struct", func() {
				invalid := Person{
					Name: "John",
					Address: Address{
						Street: "123 Main St",
					},
				}

				err := validator.ValidateStruct(invalid)
				Expect(err).To(HaveOccurred())
			})
		})

		Context("edge cases", func() {
			It("should handle struct without validation tags", func() {
				type NoValidation struct {
					Name string
					Age  int
				}

				obj := NoValidation{Name: "", Age: 0}
				err := validator.ValidateStruct(obj)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should handle empty struct", func() {
				type EmptyStruct struct{}

				obj := EmptyStruct{}
				err := validator.ValidateStruct(obj)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should handle primitive types", func() {
				err := validator.ValidateStruct("string")
				Expect(err).NotTo(HaveOccurred())

				err = validator.ValidateStruct(123)
				Expect(err).NotTo(HaveOccurred())

				err = validator.ValidateStruct(true)
				Expect(err).NotTo(HaveOccurred())
			})
		})
	})

	Describe("SliceValidationError", func() {
		It("should format single error correctly", func() {
			err := SliceValidationError{
				nil,
				errors.New("error at index 1"),
				nil,
			}

			errMsg := err.Error()
			Expect(errMsg).To(ContainSubstring("[1]"))
			Expect(errMsg).To(ContainSubstring("error at index 1"))
		})

		It("should format multiple errors correctly", func() {
			err := SliceValidationError{
				errors.New("error 0"),
				nil,
				errors.New("error 2"),
			}

			errMsg := err.Error()
			Expect(errMsg).To(ContainSubstring("[0]"))
			Expect(errMsg).To(ContainSubstring("error 0"))
			Expect(errMsg).To(ContainSubstring("[2]"))
			Expect(errMsg).To(ContainSubstring("error 2"))
			Expect(errMsg).NotTo(ContainSubstring("[1]"))
		})

		It("should return empty string for empty error slice", func() {
			err := SliceValidationError{}
			Expect(err.Error()).To(Equal(""))
		})

		It("should return empty string for slice with only nil", func() {
			err := SliceValidationError{nil, nil, nil}
			Expect(err.Error()).To(Equal(""))
		})

		It("should separate multiple errors with newline", func() {
			err := SliceValidationError{
				errors.New("first"),
				errors.New("second"),
			}

			errMsg := err.Error()
			Expect(errMsg).To(ContainSubstring("\n"))
		})
	})

	Describe("Engine", func() {
		It("should return validator instance", func() {
			engine := validator.Engine()
			Expect(engine).NotTo(BeNil())
		})

		It("should return same validator instance", func() {
			engine1 := validator.Engine()
			engine2 := validator.Engine()
			Expect(engine1).To(Equal(engine2))
		})
	})
})
