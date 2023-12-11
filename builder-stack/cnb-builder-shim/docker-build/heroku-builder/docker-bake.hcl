variable "BUILDER_IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/builder-heroku-bionic"
}

variable "BUILDER_IMAGE_TAG" {
  default = "latest"
}

variable "IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/bk-builder-heroku-bionic"
}

variable "IMAGE_TAG" {
  default = "latest"
}

target "heroku-builder" {
  dockerfile = "docker-build/heroku-builder/Dockerfile"
  args = {
    BUILDER_IMAGE_NAME = "${BUILDER_IMAGE_NAME}"
    BUILDER_IMAGE_TAG = "${BUILDER_IMAGE_TAG}"
  }
  tags = ["${IMAGE_NAME}:${IMAGE_TAG}"]
  platforms = ["linux/amd64"]
}
