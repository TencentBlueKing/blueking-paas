<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="475"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="40" y="20" rx="1" ry="1" width="180" height="20" />
        <rect x="240" y="20" rx="1" ry="1" width="180" height="20" />
        <rect x="240" y="60" rx="2" ry="2" width="680" height="42" />
        <rect x="240" y="115" rx="2" ry="2" width="680" height="15" />
        <rect x="40" y="150" rx="1" ry="1" width="180" height="20" />
        <rect x="240" y="150" rx="1" ry="1" width="180" height="20" />
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
