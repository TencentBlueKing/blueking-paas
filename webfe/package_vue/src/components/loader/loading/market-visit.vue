
<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="307"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="62" rx="2" ry="2" :width="baseWidth" height="106" /> 
        <rect x="52" y="26" rx="1" ry="1" width="501" height="16" /> 
        <rect x="52" y="0" rx="1" ry="1" width="182" height="20" /> 
        <rect x="0" y="137" rx="2" ry="2" width="293" height="16" /> 
        <rect x="0" y="0" rx="2" ry="2" width="42" height="42" />
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
