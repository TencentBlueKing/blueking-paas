<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="300"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="2" y="49" rx="2" ry="2" width="1140" height="42" /> 
        <rect x="2" y="104" rx="1" ry="1" width="1140" height="20" /> 
        <rect x="2" y="145" rx="1" ry="1" width="1140" height="20" /> 
        <rect x="2" y="186" rx="1" ry="1" width="1140" height="20" /> 
        <rect x="2" y="227" rx="1" ry="1" width="1140" height="20" /> 
        <rect x="2" y="268" rx="1" ry="1" width="1140" height="20" /> 
        <rect x="2" y="9" rx="1" ry="1" width="31" height="16" /> 
        <rect x="207" y="9" rx="1" ry="1" width="44" height="16" /> 
        <rect x="47" y="1" rx="2" ry="2" width="150" height="32" /> 
        <rect x="627" y="1" rx="2" ry="2" width="68" height="32" /> 
        <rect x="265" y="1" rx="2" ry="2" width="350" height="32" />
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
