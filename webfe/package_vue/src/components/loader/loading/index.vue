<template>
    <content-loader
        :width="baseWidth"
        :height="380"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="865" y="9" rx="1" ry="1" width="84" height="16" /> 
        <rect x="0" y="7" rx="1" ry="1" width="84" height="20" /> 
        <rect x="0" y="47" rx="2" ry="2" :width="baseWidth" height="62" /> 
        <rect x="0" y="118" rx="2" ry="2" :width="baseWidth" height="62" /> 
        <rect x="0" y="191" rx="2" ry="2" :width="baseWidth" height="62" /> 
        <rect x="0" y="264" rx="2" ry="2" :width="baseWidth" height="62" /> 
        <rect x="0" y="337" rx="2" ry="2" :width="baseWidth" height="28" /> 
        <rect x="967" y="9" rx="1" ry="1" width="58" height="16" /> 
        <rect x="1060" y="0" rx="2" ry="2" width="120" height="36" />
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