<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="170"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="19" y="137" rx="1" ry="1" width="73" height="16" /> 
        <rect x="116" y="136" rx="1" ry="1" width="64" height="17" /> 
        <rect x="206" y="136" rx="1" ry="1" width="64" height="16" /> 
        <path d="M 0 167 h 1180 v 1 H 0 z" /> 
        <rect x="0" y="0" rx="2" ry="2" width="1180" height="106" /> 
        <rect x="644" y="188" rx="2" ry="2" width="68" height="32" />
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
