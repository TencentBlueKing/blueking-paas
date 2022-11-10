<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="505"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="96" rx="2" ry="2" width="1180" height="42" /> 
        <rect x="0" y="151" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="192" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="233" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="274" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="315" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="356" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="44" rx="2" ry="2" width="1180" height="36" /> 
        <rect x="0" y="0" rx="1" ry="1" width="64" height="16" /> 
        <path d="M 0 32 h 1180 v 1 H 0 z" />
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