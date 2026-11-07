# 来源与实施记录

来源 HTML 下载成功。趋势词位于 section#trending 内的 .trend-tag，分组标题 .trend-group-title，子组 .trend-subgroup-label。并非动态 API。原页面说明数据不是实时数据。

本机 python 可用，git/gh/node/npm 不在 PATH，未发现 GitHub 令牌环境变量名称。已向用户询问目标仓库。

网络沙箱直连失败；提升权限后 curl 成功读取用户指定公开网页。

最终验证：python tracker.py 直接联网成功，73 个去重词 / 4 分类；3 项 unittest 全部通过。GitHub Pages 配置参考官方 custom workflows 文档，上传 artifact 使用 v4。线上工作流尚未执行。
