<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="500"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" width="120" height="26" />
        <rect x="0" y="46" rx="2" ry="2" width="200" height="130" />
        <rect x="220" y="46" rx="2" ry="2" width="180" height="26" />
        <rect x="220" y="98" rx="2" ry="2" width="480" height="26" />
        <rect x="220" y="150" rx="2" ry="2" width="180" height="26" />
        
        <rect x="0" y="210" rx="2" ry="2" width="120" height="26" />
        <rect x="30" y="256" rx="2" ry="2" width="130" height="26" />
        <rect x="180" y="256" rx="2" ry="2" width="280" height="26" />
        <rect x="30" y="296" rx="2" ry="2" width="130" height="26" />
        <rect x="180" y="296" rx="2" ry="2" width="240" height="26" />
        <rect x="30" y="336" rx="2" ry="2" width="130" height="26" />
        <rect x="180" y="336" rx="2" ry="2" width="180" height="26" />
        <rect x="30" y="376" rx="2" ry="2" width="130" height="26" />
        <rect x="180" y="376" rx="2" ry="2" width="280" height="26" />
        <rect x="30" y="416" rx="2" ry="2" width="130" height="26" />
        <rect x="180" y="416" rx="2" ry="2" width="220" height="26" />
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
