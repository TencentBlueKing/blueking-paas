<template>
    <content-loader
        :width="360"
        :height="200"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
    >
        <rect x="0" y="151" rx="2" ry="2" width="40" height="62" /> 
        <rect x="90" y="119" rx="2" ry="2" width="40" height="94" /> 
        <rect x="180" y="57" rx="2" ry="2" width="40" height="156" /> 
        <rect x="270" y="77" rx="2" ry="2" width="40" height="136" /> 
        <rect x="360" y="200" rx="2" ry="2" width="40" height="13" /> 
        <rect x="105" y="0" rx="1" ry="1" width="191" height="20" />
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