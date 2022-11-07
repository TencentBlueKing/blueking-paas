<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="505"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="24" rx="1" ry="1" width="420" height="16" /> 
        <rect x="0" y="193" rx="1" ry="1" width="420" height="16" /> 
        <rect x="0" y="169" rx="1" ry="1" width="160" height="20" /> 
        <rect x="0" y="0" rx="1" ry="1" width="160" height="20" /> 
        <rect x="0" y="60" rx="2" ry="2" width="580" height="93" /> 
        <rect x="0" y="226" rx="2" ry="2" width="580" height="93" /> 
        <rect x="0" y="423" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="465" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="1" y="389" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="365" rx="1" ry="1" width="100" height="20" /> 
        <rect x="600" y="60" rx="2" ry="2" width="580" height="93" /> 
        <rect x="600" y="226" rx="2" ry="2" width="580" height="93" />
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