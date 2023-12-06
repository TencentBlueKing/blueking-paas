variable "BUILDER_IMAGE" {
  default = "mirrors.tencent.com/bkpaas/heroku-builder"
}

variable "BUILDER_TAG" {
  default = "bionic"
}

variable "IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/heroku-builder-all-in-one"
}

variable "IMAGE_TAG" {
  default = "bionic"
}

target "heroku-builder" {
  dockerfile = "docker-build/heroku-builder/Dockerfile"
  args = {
    BUILDER_IMAGE = "${BUILDER_IMAGE}"
    BUILDER_TAG = "${BUILDER_TAG}"
  }
  tags = ["${IMAGE_NAME}:${IMAGE_TAG}"]
}
