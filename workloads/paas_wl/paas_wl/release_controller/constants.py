from blue_krill.data_types.enum import EnumField, StructuredEnum


class RuntimeType(str, StructuredEnum):
    BUILDPACK = EnumField("buildpack", label="Runtime for buildpack")
    CUSTOM_IMAGE = EnumField("custom_image", label="Custom Image")
    BK_SMART = EnumField("bk-smart", label="Runtime for buildpack, but build as image")


class ImagePullPolicy(str, StructuredEnum):
    ALWAYS = EnumField("Always")
    IF_NOT_PRESENT = EnumField("IfNotPresent")
    NEVER = EnumField("Never")
