<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="571"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="98" rx="2" ry="2" width="1180" height="42" /> 
        <rect x="0" y="153" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="194" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="235" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="276" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="317" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="358" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="622" y="57" rx="1" ry="1" width="54" height="16" /> 
        <rect x="0" y="49" rx="2" ry="2" width="116" height="32" /> 
        <rect x="685" y="49" rx="2" ry="2" width="240" height="32" /> 
        <rect x="940" y="49" rx="2" ry="2" width="240" height="32" /> 
        <rect x="125" y="49" rx="2" ry="2" width="68" height="32" /> 
        <rect x="0" y="0" rx="1" ry="1" width="74" height="16" /> 
        <rect x="98" y="0" rx="1" ry="1" width="87" height="16" /> 
        <path d="M 0 28 h 1180 v 1 H 0 z" />
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
