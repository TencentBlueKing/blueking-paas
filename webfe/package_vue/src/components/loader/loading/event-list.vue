<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="520"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="55" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="96" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="137" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="178" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="219" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="260" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="301" rx="1" ry="1" :width="160" height="32" /> 
        <rect :x="contentWidth" y="301" rx="1" ry="1" :width="120" height="32" /> 
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
