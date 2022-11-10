<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="571"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="8" rx="2" ry="2" :width="baseWidth" height="20" />
        <rect x="0" y="41" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="74" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="110" rx="2" ry="2" width="80" height="28" />
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
