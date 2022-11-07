<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="571"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="8" rx="2" ry="2" :width="baseWidth" height="42" />
        <rect x="0" y="63" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="104" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="145" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="186" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="227" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="268" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="309" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="350" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="391" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="432" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="489" rx="2" ry="2" width="126" height="32" />
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
