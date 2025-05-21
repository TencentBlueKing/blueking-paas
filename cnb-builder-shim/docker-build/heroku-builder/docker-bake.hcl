variable "BUILDER_IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/builder-heroku-noble"
}

variable "BUILDER_IMAGE_TAG" {
  default = "latest"
}

variable "IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/bk-builder-heroku-noble"
}

variable "IMAGE_TAG" {
  default = "latest"
}

variable "DEV_IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/bk-dev-heroku-noble"
}

variable "DEV_IMAGE_TAG" {
  default = "latest"
}

target "heroku-builder-noble" {
  dockerfile = "docker-build/heroku-builder/Dockerfile"
  args = {
    BUILDER_IMAGE_NAME = "${BUILDER_IMAGE_NAME}"
    BUILDER_IMAGE_TAG = "${BUILDER_IMAGE_TAG}"
  }
  tags = ["${IMAGE_NAME}:${IMAGE_TAG}"]
  platforms = ["linux/amd64"]
}

target "heroku-dev" {
  dockerfile = "docker-build/heroku-builder/dev.Dockerfile"

  args = {
    BUILDER_IMAGE_NAME = "${BUILDER_IMAGE_NAME}"
    BUILDER_IMAGE_TAG = "${BUILDER_IMAGE_TAG}"
  }

  tags = ["${DEV_IMAGE_NAME}:${DEV_IMAGE_TAG}"]
  platforms = ["linux/amd64"]
}
