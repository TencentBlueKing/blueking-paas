<template>
    <content-loader
        :width="baseWidth"
        :height="779"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="34" rx="1" ry="1" width="510" height="16" /> 
        <rect x="0" y="0" rx="1" ry="1" width="160" height="20" /> 
        <rect x="130" y="92" rx="2" ry="2" width="134" height="20" /> 
        <rect x="523" y="92" rx="2" ry="2" width="134" height="20" /> 
        <rect x="916" y="92" rx="2" ry="2" width="134" height="20" /> 
        <rect x="0" y="223" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="471" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="347" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="595" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="719" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="161" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="409" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="285" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="533" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="657" rx="2" ry="2" :width="baseWidth" height="60" /> 
        <rect x="0" y="115" rx="2" ry="2" :width="baseWidth" height="42" />
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
