<template>
    <content-loader
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :width="baseWidth"
        :height="220"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" width="128" height="32" /> 
        <rect x="130" y="0" rx="2" ry="2" width="128" height="32" /> 
        <rect x="260" y="0" rx="2" ry="2" width="128" height="32" /> 
        <rect x="390" y="0" rx="2" ry="2" width="128" height="32" /> 
        <rect x="0" y="52" rx="2" ry="2" width="286" height="168" /> 
        <rect x="298" y="52" rx="2" ry="2" width="286" height="168" /> 
        <rect x="596" y="52" rx="2" ry="2" width="286" height="168" /> 
        <rect x="894" y="52" rx="2" ry="2" width="286" height="168" />
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
