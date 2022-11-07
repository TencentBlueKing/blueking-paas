<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="505"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="83" y="0" rx="2" ry="2" width="73" height="20" />
        <rect x="0" y="79" rx="2" ry="2" width="64" height="20" />
        <rect x="0" y="150" rx="2" ry="2" width="87" height="20" />
        <rect x="83" y="28" rx="2" ry="2" width="410" height="16" />
        <rect x="0" y="113" rx="2" ry="2" width="493" height="16" />
        <rect x="0" y="184" rx="2" ry="2" width="493" height="16" />
        <rect x="0" y="218" rx="2" ry="2" width="580" height="90" />
        <rect x="0" y="0" rx="4" ry="4" width="64" height="64" />
    </content-loader>
</template>

<script>
    import { ContentLoader } from 'vue-content-loader'
    export default {
        components: {
            ContentLoader
        },
        props: {
            baseWidth: {
                type: Number,
                default: 1180
            },
            contentWidth: {
                type: Number,
                default: 1180
            }
        },
        computed: {
            loadingConf () {
                return this.$store.state.loadingConf
            }
        }
    }
</script>