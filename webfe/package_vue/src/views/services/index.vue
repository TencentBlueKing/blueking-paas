<template lang="html">
  <div class="right-main">
    <div class="ps-top-bar">
      <h2> {{ $t('增强服务') }} </h2>
    </div>
    <div class="service">
      <div class="middle bnone">
        <h4> {{ $t('数据存储') }} </h4>
        <ul class="service-list">
          <li>
            <router-link to="/developer-center/service/mySQL">
              <img
                :src="servicePic2"
                class="service-list-img"
              >
              <span class="service-list-tit">MySQL</span>
              <span class="service-list-con"> {{ $t('通过在应用内配置『钩子』捕获应用错误信息') }} </span>
            </router-link>
          </li>
          <li>
            <router-link to="/developer-center/service/Redis">
              <img
                :src="servicePic3"
                class="service-list-img"
              >
              <span class="service-list-tit">Redis</span>
              <span class="service-list-con">Key-Value {{ $t('存储') }}</span>
            </router-link>
          </li>
          <li>
            <router-link to="/developer-center/service/RabbitMQ">
              <img
                :src="servicePic4"
                class="service-list-img"
              >
              <span class="service-list-tit">RabbitMQ</span>
              <span class="service-list-con"> {{ $t('可用于存储图片等文件') }} </span>
            </router-link>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  data() {
    return {
      servicePic2: require('@static/images/service-pic2.png'),
      servicePic3: require('@static/images/service-pic3.png'),
      servicePic4: require('@static/images/service-pic4.png'),
    };
  },
};
</script>
