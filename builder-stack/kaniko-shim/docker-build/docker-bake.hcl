variable "IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/kaniko-executor"
}

variable "IMAGE_TAG" {
  default = "latest"
}

target "kaniko-executor" {
  dockerfile = "docker-build/Dockerfile"
  tags = ["${IMAGE_NAME}:${IMAGE_TAG}"]
  platforms = ["linux/amd64"]
}

target "kaniko-debug-executor" {
  dockerfile = "docker-build/Dockerfile_debug"
  tags = ["${IMAGE_NAME}:debug"]
  platforms = ["linux/amd64"]
}
