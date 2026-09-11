module.exports = (middlewares, devServer) => {
  /** mock 接口 */
  require('../paas-server/api/table')(devServer.app);
  return middlewares;
};
