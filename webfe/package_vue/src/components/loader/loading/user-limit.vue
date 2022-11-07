<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="407"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="53" y="24" rx="1" ry="1" width="501" height="16" /> 
        <rect x="0" y="0" rx="2" ry="2" width="42" height="42" /> 
        <rect x="53" y="0" rx="1" ry="1" width="182" height="20" /> 
        <rect x="0" y="79" rx="2" ry="2" width="120" height="32" /> 
        <rect x="0" y="127" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="182" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="223" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="264" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="305" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="346" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="387" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="130" y="79" rx="2" ry="2" width="88" height="32" /> 
        <rect x="940" y="79" rx="2" ry="2" width="240" height="32" /> 
        <rect x="228" y="87" rx="1" ry="1" width="74" height="16" />
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
