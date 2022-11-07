<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="557"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="328" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="100" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="370" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="142" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="184" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="1" y="24" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="294" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="464" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="541" rx="1" ry="1" width="96" height="16" /> 
        <rect x="1" y="270" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="440" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="499" rx="1" ry="1" width="88" height="32" /> 
        <rect x="1" y="0" rx="1" ry="1" width="100" height="20" />
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