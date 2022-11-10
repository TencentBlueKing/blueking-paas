<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="328"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
        >
        <rect x="0" y="48" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="103" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="144" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="185" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="226" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="267" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="308" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="0" rx="2" ry="2" width="120" height="32" /> 
        <rect x="384" y="0" rx="2" ry="2" width="184" height="32" /> 
        <rect x="580" y="0" rx="2" ry="2" width="146" height="32" /> 
        <rect x="742" y="0" rx="2" ry="2" width="68" height="32" /> 
        <rect x="132" y="0" rx="2" ry="2" width="240" height="32" />
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
