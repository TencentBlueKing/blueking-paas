<template lang="html">
  <div class="right-main">
    <div class="ps-top-bar">
      <h2 v-if="categoryId === 1">
        {{ $t('数据存储') }}
      </h2>
      <h2 v-else-if="categoryId === 2">
        {{ $t('健康监测') }}
      </h2>
    </div>
    <div class="ps-container service-container card-style">
      <paas-content-loader
        class="middle bnone"
        :is-loading="isLoading"
        placeholder="service-loading"
      >
        <div
          class="category-list"
          v-if="categoryObject.services && categoryObject.services?.length"
        >
          <ul class="service-list">
            <li
              v-for="(service, index) in categoryObject.services"
              :key="index"
              class="text-ellipsis"
            >
              <router-link :to="{ name: 'serviceInnerPage', params: { category_id: categoryId, name: service.name } }">
                <img
                  :src="service.logo"
                  class="service-list-img"
                  alt=""
                />
                <span class="service-list-tit">{{ service.display_name }}</span>
                <span class="service-list-con">{{ service.description }}</span>
              </router-link>
            </li>
          </ul>
        </div>

        <div
          v-else
          style="height: 250px"
        >
          <div class="ps-no-result text">
            <table-empty
              :empty-title="$t('暂无增强服务')"
              empty
            />
          </div>
        </div>
      </paas-content-loader>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      isLoading: false,
      categoryId: '',

      categoryObject: {
        services: [],
      },
    };
  },
  watch: {
    $route() {
      this.categoryId = Number(this.$route.params.category_id);
      this.categoryObject = Object.assign(
        {},
        {
          services: [],
        }
      );
      this.fetchCategoryInfo();
    },
  },
  async created() {
    this.categoryId = Number(this.$route.params.category_id);
    this.fetchCategoryInfo();
  },
  methods: {
    tabChange(tab) {
      const tempServices = [];
      this.categoryObject.all.services.forEach((item) => {
        if (item.enabled_regions.includes(tab)) {
          tempServices.push(item);
        }
      });

      this.categoryObject[tab].services = [...tempServices];
    },
    fetchCategoryInfo() {
      this.isLoading = true;
      this.$http.get(`${BACKEND_URL}/api/services/categories/${this.categoryId}/`).then((response) => {
        const resData = response;

        this.categoryObject.services = [...resData.results];
        this.isLoading = false;
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.service-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.service-list li {
  box-sizing: border-box;
}

.service-list li.on,
.service-list li:hover {
  a {
    border: solid 1px #3a84ff;
    box-shadow: 0 0 1px #5cadff;
  }
}

.service-list li a {
  width: 100%;
  display: block;
  height: 168px;
  border: solid 1px #e6e9ea;
  border-radius: 2px;
  text-align: center;
  transition: all 0.5s;
}

.service-list-img {
  display: block;
  margin: 24px auto auto auto;
  height: 48px;
}

.service-list-tit {
  display: block;
  padding: 10px 0;
  height: 34px;
  line-height: 34px;
  font-weight: bold;
  color: #5d6075;
  overflow: hidden;
}

.service-list-con {
  display: block;
  padding: 0 15px;
  height: 40px;
  line-height: 20px;
  color: #666;
  font-size: 12px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.service-container {
  margin-top: 16px;
  background: #fff;
  padding: 16px;
  min-height: 260px;
}
</style>
