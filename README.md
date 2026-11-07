# Fashion Edit 趋势词观察

采集 https://fashion-edit-merchant.netlify.app/#trending 的公开热搜趋势词。Python 标准库实现，无需安装第三方依赖。

## 本地使用

需要 Python 3.11 或更高版本。

```powershell
python tracker.py
python -m http.server 8000 --directory docs
```

浏览器打开 http://localhost:8000 。支持关键词搜索、只看新增、分类浏览、JSON 下载及历史快照。

## 规则

- 每天北京时间 09:15（UTC 01:15）由 GitHub Actions 抓取，调度可能延迟。
- 首次运行建立基线，不把全部词当新增。后续相对上一成功采集日期比较；重新出现的词也标红并显示 NEW。
- 同一天重复抓取仍对比上一日期，保留当日新增标记；第二天无变化则清除标红。
- 每日保存最新一次成功快照，保留全部日期历史；首次收录日期可追溯。
- Unicode、空格及大小写规范化去重，同词多个分类均保留。
- 来源已有的 hot 样式不是新增判定依据。来源无搜索量，不生成虚假排名或热度。
- 请求重试三次；网页结构不匹配或抓取失败时工作流失败，线上保留上一成功部署。页面显示最后成功检查时间。
- 来源是静态关键词整理，只有来源更新后才能采集到新词。

## 部署至 GitHub Pages

1. 在 GitHub 创建仓库，将项目推送至 `main` 分支。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。免费账号通常需要公开仓库才能使用 Pages。
3. 在 **Actions → Daily trends and Pages → Run workflow** 手动运行一次。
4. 成功后访问 `https://你的用户名.github.io/仓库名/`。

工作流已经配置自动保存历史和部署 Pages，无需外部 API 密钥。需要允许 Actions 对仓库写入；组织策略限制时，请管理员开放工作流写入权限。GitHub 对公开仓库长期无活动的定时工作流可能自动停用，届时手动重新启用。

```powershell
python -m unittest discover -s tests -v
```

目录：`tracker.py` 采集和生成页面；`docs/` 为 Pages 站点；`docs/data/` 保存 JSON；`.github/workflows/daily.yml` 为每日任务。
