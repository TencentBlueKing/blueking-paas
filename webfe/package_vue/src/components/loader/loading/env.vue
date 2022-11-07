<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="363"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="216" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="24" rx="1" ry="1" width="360" height="16" /> 
        <rect x="0" y="240" rx="1" ry="1" width="560" height="16" /> 
        <rect x="0" y="287" rx="1" ry="1" width="79" height="16" /> 
        <rect x="87" y="279" rx="2" ry="2" width="128" height="32" /> 
        <rect x="0" y="331" rx="2" ry="2" width="230" height="32" /> 
        <rect x="240" y="331" rx="2" ry="2" width="230" height="32" /> 
        <rect x="480" y="331" rx="2" ry="2" width="230" height="32" /> 
        <rect x="720" y="331" rx="2" ry="2" width="164" height="32" /> 
        <rect x="894" y="331" rx="2" ry="2" width="70" height="32" /> 
        <rect x="894" y="279" rx="2" ry="2" width="70" height="32" /> 
        <rect x="217" y="279" rx="2" ry="2" width="128" height="32" /> 
        <rect x="347" y="279" rx="2" ry="2" width="128" height="32" /> 
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="102" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="152" rx="2" ry="2" width="130" height="32" />
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
