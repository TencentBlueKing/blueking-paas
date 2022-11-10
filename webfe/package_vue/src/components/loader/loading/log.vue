<template>
    <content-loader
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})`, 'margin-top': '-40px' }"
        :width="baseWidth"
        :height="600"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="55" rx="1" ry="1" width="74" height="16" /> 
        <rect x="839" y="49" rx="2" ry="2" width="146" height="28" /> 
        <rect x="995" y="49" rx="2" ry="2" width="146" height="28" /> 
        <rect x="1152" y="49" rx="2" ry="2" width="28" height="28" /> 
        <rect x="1082" y="101" rx="1" ry="1" width="98" height="16" /> 
        <rect x="0" y="93" rx="2" ry="2" width="100" height="32" /> 
        <rect x="110" y="93" rx="2" ry="2" width="100" height="32" /> 
        <rect x="220" y="93" rx="2" ry="2" width="100" height="32" /> 
        <rect x="330" y="93" rx="2" ry="2" width="731" height="32" /> 
        <rect x="0" y="145" rx="2" ry="2" width="210" height="436" /> 
        <rect x="250" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="220" y="315" rx="2" ry="2" width="960" height="40" /> 
        <rect x="570" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="890" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="290" y="206" rx="2" ry="2" width="20" height="50" /> 
        <rect x="610" y="206" rx="2" ry="2" width="20" height="50" /> 
        <rect x="930" y="206" rx="2" ry="2" width="20" height="50" /> 
        <rect x="370" y="193" rx="2" ry="2" width="20" height="63" /> 
        <rect x="690" y="193" rx="2" ry="2" width="20" height="63" /> 
        <rect x="1010" y="193" rx="2" ry="2" width="20" height="63" /> 
        <rect x="330" y="221" rx="2" ry="2" width="20" height="35" /> 
        <rect x="650" y="221" rx="2" ry="2" width="20" height="35" /> 
        <rect x="970" y="221" rx="2" ry="2" width="20" height="35" /> 
        <rect x="410" y="211" rx="2" ry="2" width="20" height="45" /> 
        <rect x="730" y="211" rx="2" ry="2" width="20" height="45" /> 
        <rect x="1050" y="211" rx="2" ry="2" width="20" height="45" /> 
        <rect x="490" y="228" rx="2" ry="2" width="20" height="28" /> 
        <rect x="810" y="228" rx="2" ry="2" width="20" height="28" /> 
        <rect x="1130" y="228" rx="2" ry="2" width="20" height="28" /> 
        <rect x="530" y="206" rx="2" ry="2" width="20" height="50" /> 
        <rect x="850" y="206" rx="2" ry="2" width="20" height="50" /> 
        <rect x="450" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="770" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="1090" y="186" rx="2" ry="2" width="20" height="70" /> 
        <rect x="220" y="375" rx="1" ry="1" width="960" height="21" /> 
        <rect x="220" y="416" rx="1" ry="1" width="960" height="21" /> 
        <rect x="220" y="457" rx="1" ry="1" width="960" height="21" /> 
        <rect x="220" y="498" rx="1" ry="1" width="960" height="21" /> 
        <rect x="220" y="539" rx="1" ry="1" width="960" height="21" /> 
        <rect x="0" y="0" rx="1" ry="1" width="74" height="16" /> 
        <rect x="98" y="0" rx="1" ry="1" width="87" height="16" /> 
        <rect x="210" y="0" rx="1" ry="1" width="87" height="16" /> 
        <rect x="1076" y="0" rx="1" ry="1" width="104" height="16" /> 
        <path d="M 0 28 h 1180 v 1 H 0 z" />
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