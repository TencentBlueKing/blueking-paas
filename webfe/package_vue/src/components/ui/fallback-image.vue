<template>
    <img :src="imageSrc" :class="cls" :alt="alt" ref="img">
</template>
<script>
    export default {
        name: 'fallback-image',
        props: {
            url: {
                type: String
            },
            urlFallback: {
                type: String
            },
            cls: {
                type: String
            },
            alt: {
                type: String,
                default: 'user'
            }
        },
        data () {
            return {
                imageSrc: this.url || this.urlFallback
            };
        },
        mounted () {
            this.$refs.img.onerror = () => {
                this.imageSrc = this.urlFallback;
            };

            this.$refs.img.onload = () => {
                this.$emit('load-callback', this.$refs.img.src);
            };
        }
    };
</script>
