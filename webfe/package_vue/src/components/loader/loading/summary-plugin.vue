<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="742"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" width="58" height="16" /> 
        <rect x="0" y="45" rx="2" ry="2" width="900" height="68" /> 
        <rect x="0" y="165" rx="2" ry="2" width="120" height="30" /> 
        <rect x="660" y="165" rx="2" ry="2" width="240" height="30" /> 
        <rect x="0" y="220" rx="2" ry="2" width="900" height="440" /> 
        <rect x="937" y="58" rx="2" ry="2" width="80" height="16" /> 
        <rect x="937" y="249" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="292" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="375" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="456" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="537" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="616" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="699" rx="2" ry="2" width="80" height="16" /> 
        <rect x="960" y="313" rx="2" ry="2" width="920" height="16" /> 
        <rect x="960" y="396" rx="2" ry="2" width="920" height="16" /> 
        <rect x="960" y="477" rx="2" ry="2" width="220" height="16" /> 
        <rect x="960" y="558" rx="2" ry="2" width="220" height="16" /> 
        <rect x="960" y="637" rx="2" ry="2" width="220" height="16" /> 
        <rect x="960" y="720" rx="2" ry="2" width="220" height="16" /> 
        <rect x="937" y="109" rx="2" ry="2" width="118" height="16" /> 
        <rect x="937" y="141" rx="2" ry="2" width="118" height="16" /> 
        <rect x="937" y="175" rx="2" ry="2" width="243" height="32" /> 
        <path d="M 919 32 h 1 v 775 h -1 z" /> 
        <circle cx="947" cy="299" r="5" /> 
        <circle cx="947" cy="380" r="5" /> 
        <circle cx="947" cy="461" r="5" /> 
        <circle cx="947" cy="542" r="5" /> 
        <circle cx="947" cy="623" r="5" /> 
        <circle cx="947" cy="704" r="5" /> 
        <circle cx="947" cy="785" r="5" /> 
        <path d="M 947 304 h 1 v 481 h -1 z" />
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
