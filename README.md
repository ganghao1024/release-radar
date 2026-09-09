# 发布雷达 · Release Radar

手机新品与 AI 模型的官方发布信息流。Python 定时采集，原生 HTML/CSS/JavaScript 静态网页，通过 GitHub Actions 部署到 GitHub Pages，无需模型 API Key 或常开服务器。

## 功能

- 手机、AI 两个频道；搜索、厂商、发布阶段、时间范围筛选。
- 官方 RSS/Atom 与官网公告解析；每条记录保留原文链接与日期。
- 发布、预览、上线与待核实线索分开；不把采集时间当成发布日期。
- URL 去重、来源故障保留记录、180 天归档、源健康状态。
- 厂商关系目录、实时来源清单、可下载 Markdown 和聚合 RSS。
- 适配桌面与手机，原生键盘可访问控件。

## 本地运行

需要 Python 3.11+。Node.js 仅用于可选的 npm 命令封装，运行网页不依赖 Node。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/collect.py
python scripts/build.py
python -m http.server 4173 --directory dist
```

浏览器打开 `http://localhost:4173`。不能直接双击 HTML，因为浏览器会限制本地文件读取 JSON。

## 文档

- 厂商关系清单：本地生成 `docs/厂商与品牌关系.md`，不上传、不发布。
- 数据源清单：本地生成 `docs/数据源列表.md`，不上传、不发布。
- [部署、运行机制与维护](docs/部署与维护.md)

## 配置

`config/catalog.json` 是 95 条目录关系；`config/sources.json` 区分已启用适配器与候选官方入口；`config/site.json` 保存站点和仓库公开地址。直接修改 JSON 后运行采集和构建即可。

`scripts/catalog.py` 与 `scripts/sources.py` 是初始目录生成工具，日常更新应修改 JSON，不要重新运行生成工具覆盖自己的配置。

`data/latest.json` 是实际抓取快照，作为无缓存时的初始数据；不是示例新闻。每次 Actions 从缓存恢复历史，重新采集并发布。Actions 的 `source-audit` artifact 仅保存数据快照；两份清单文档只在本地保留。手机仅使用中国大陆官网，国际手机历史记录会自动过滤。

## 发布判断边界

关键词规则用于发现线索，不保证新闻完整性，也不保证每条均为全新型号或模型。正文语义未由大模型复核；产品小更新可能被收录。RSS 窗口、官网动态页面、反爬、源停更会影响覆盖。目录内候选品牌不计入采集覆盖率。按 URL 去重，同厂商、同地区、同日、同阶段且标题完全相同的转载会合并并保留原始链接；不做跨语言语义合并，避免误删开售等后续事件。

## 参考

采集与静态发布思路参考 [SuYxh/ai-news-aggregator](https://github.com/SuYxh/ai-news-aggregator)。此仓库为独立实现，没有复制上游代码或图片。

项目代码采用 MIT 许可；源文章内容归各来源权利人所有。
