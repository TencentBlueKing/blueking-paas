<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="307"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="116" rx="2" ry="2" :width="baseWidth" height="106" /> 
        <rect x="52" y="80" rx="1" ry="1" width="501" height="16" /> 
        <rect x="52" y="54" rx="1" ry="1" width="182" height="20" /> 
        <rect x="0" y="0" rx="1" ry="1" width="64" height="16" /> 
        <rect x="84" y="0" rx="1" ry="1" width="88" height="16" /> 
        <path d="M 0 28 h 1180 v 1 H 0 z M 0 250 h 1180 v 1 H 0 z" /> 
        <rect x="0" y="291" rx="2" ry="2" width="293" height="16" /> 
        <rect x="0" y="54" rx="2" ry="2" width="42" height="42" />
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
