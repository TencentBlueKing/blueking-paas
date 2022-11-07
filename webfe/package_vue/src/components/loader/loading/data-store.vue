<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="500"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="34" rx="2" ry="2" width="286" height="174" /> 
        <rect x="0" y="266" rx="2" ry="2" width="286" height="174" /> 
        <rect x="298" y="266" rx="2" ry="2" width="286" height="174" /> 
        <rect x="596" y="266" rx="2" ry="2" width="286" height="174" /> 
        <rect x="0" y="0" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="232" rx="1" ry="1" width="100" height="20" />
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
