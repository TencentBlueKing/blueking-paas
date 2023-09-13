<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="500"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" width="120" height="26" />
        <rect x="40" y="46" rx="2" ry="2" width="120" height="26" />
        <rect x="180" y="46" rx="2" ry="2" width="80" height="26" />
        <rect x="40" y="86" rx="2" ry="2" width="120" height="26" />
        <rect x="180" y="86" rx="2" ry="2" width="380" height="26" />
        <rect x="40" y="126" rx="2" ry="2" width="120" height="26" />
        <rect x="180" y="126" rx="2" ry="2" width="180" height="26" />
        
        <rect x="0" y="190" rx="2" ry="2" width="120" height="26" />
        <rect x="140" y="190" rx="2" ry="2" width="280" height="26" />
        <rect x="40" y="230" rx="2" ry="2" width="120" height="26" />
        <rect x="180" y="230" rx="2" ry="2" width="180" height="26" />
        <rect x="40" y="270" rx="2" ry="2" width="120" height="26" />
        <rect x="180" y="270" rx="2" ry="2" width="180" height="26" />

        <rect x="0" y="330" rx="2" ry="2" width="120" height="26" />
        <rect x="140" y="330" rx="2" ry="2" width="320" height="26" />
        <rect x="40" y="370" rx="2" ry="2" width="80" height="26" />
        <rect x="130" y="370" rx="2" ry="2" width="220" height="120" />
        <rect x="370" y="370" rx="2" ry="2" width="80" height="26" />
        <rect x="460" y="370" rx="2" ry="2" width="220" height="120" />
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
