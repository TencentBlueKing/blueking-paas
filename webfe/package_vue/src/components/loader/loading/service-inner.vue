<template>
    <content-loader
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :width="baseWidth"
        :height="589"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="350" rx="2" ry="2" width="1180" height="42" /> 
        <rect x="0" y="405" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="446" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="487" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="528" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="0" y="569" rx="1" ry="1" width="1180" height="20" /> 
        <rect x="89" y="8" rx="2" ry="2" width="341" height="20" /> 
        <rect x="89" y="42" rx="2" ry="2" width="59" height="22" /> 
        <rect x="152" y="42" rx="2" ry="2" width="59" height="22" /> 
        <rect x="0" y="0" rx="6" ry="6" width="64" height="64" /> 
        <rect x="0" y="123" rx="1" ry="1" width="180" height="16" /> 
        <rect x="0" y="198" rx="1" ry="1" width="180" height="16" /> 
        <rect x="0" y="273" rx="1" ry="1" width="180" height="16" /> 
        <rect x="0" y="91" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="166" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="241" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="312" rx="1" ry="1" width="180" height="20" />
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
