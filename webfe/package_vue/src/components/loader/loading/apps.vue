<template>
    <content-loader
        :width="baseWidth"
        :height="552"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
    >
        <rect x="0" y="55" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="131" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="207" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="283" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="359" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="435" rx="2" ry="2" :width="baseWidth" height="64" /> 
        <rect x="0" y="5" rx="1" ry="1" width="99" height="20" /> 
        <rect x="564" y="8" rx="1" ry="1" width="84" height="16" /> 
        <rect x="763" y="0" rx="2" ry="2" width="417" height="32" /> 
        <rect x="665" y="0" rx="2" ry="2" width="88" height="32" /> 
        <rect x="0" y="520" rx="2" ry="2" width="104" height="32" /> 
        <rect x="1076" y="520" rx="2" ry="2" width="104" height="32" />
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