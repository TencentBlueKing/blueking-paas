<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="600"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <!-- <rect x="0" y="0" rx="2" ry="2" width="150" height="32" />  -->
        <rect x="0" y="0" rx="2" ry="2" width="80" height="32" /> 
        <rect x="920" y="0" rx="2" ry="2" width="240" height="32" /> 
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="32" /> 
        <rect x="0" y="113" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="154" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="195" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="236" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="277" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="318" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="359" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <!--  -->
        <rect x="0" y="400" rx="1" ry="1" width="100" height="32" /> 
        <rect x="1040" y="400" rx="1" ry="1" width="120" height="32" /> 
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
