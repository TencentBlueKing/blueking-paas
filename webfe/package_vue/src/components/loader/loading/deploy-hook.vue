<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="328"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" width="120" height="24" />
        <rect x="130" y="0" rx="2" ry="2" width="80" height="24" />
        <rect x="220" y="0" rx="2" ry="2" width="60" height="24" />
        <rect x="20" y="44" rx="2" ry="2" width="120" height="20" />
        <rect x="160" y="44" rx="2" ry="2" width="200" height="20" />
        <rect x="20" y="84" rx="2" ry="2" width="120" height="20" />
        <rect x="160" y="84" rx="2" ry="2" width="200" height="20" />
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
