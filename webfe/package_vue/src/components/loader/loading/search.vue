<template>
    <content-loader
        :width="baseWidth"
        :height="850"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="48" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="124" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="352" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="656" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="200" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="504" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="428" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="732" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="276" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="580" rx="2" ry="2" :width="baseWidth" height="66" /> 
        <rect x="0" y="0" rx="1" ry="1" width="64" height="16" /> 
        <rect x="92" y="0" rx="1" ry="1" width="64" height="16" /> 
        <rect x="184" y="0" rx="1" ry="1" width="64" height="16" /> 
        <rect x="276" y="0" rx="1" ry="1" width="64" height="16" /> 
        <path d="M 0 27 h 1180 v 1 H 0 z" /> 
        <rect x="0" y="818" rx="2" ry="2" width="126" height="32" /> 
        <rect x="1021" y="818" rx="2" ry="2" width="159" height="32" />
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
