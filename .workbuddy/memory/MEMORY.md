# MEMORY.md - 长期记忆

## 项目位置

- **obsidian-eg 工作区**：`E:\Notes\obsidian-eg`（Obsidian 词汇知识库主仓库）
- **vocab-observatory**：`E:\Projects\vocab-observatory`（Next.js 网站，数据源为 obsidian-eg）

## vocab-observatory 数据管道

- 架构：Obsidian → GitHub → Supabase → Vercel
- 同步入口：`POST /api/imports/github` 或 `npm run sync:vault`
- 数据流：GitHub Archive → JSZip → parseMarkdown → Supabase upsert → ISR 缓存
- 默认内容源：`zc63463-cmyk/Obsidian-Eg` 仓库的 `Wiki/L0_单词集合/` 目录
- 当前状态：5249 词条已批量修正模板格式（2026-04-26 commit 213b5ec8），网站可访问
- Wiki 层（词根/语义场/形近字）质量极不均，需重建
- 重建指令文件在 `Wiki/_系统/_Trae-B{0-4}*.md` 和 `_Trae-Wiki层重建主指令.md`
- 首页 AnimatedCounter 显示 0 是 SSR 快照的客户端组件初始化值，非实际 bug
- 模板/规范文件统一存放在 `Wiki/_系统/` 目录下

## 技术栈

- vocab-observatory：Next.js 16.2.4 + Turbopack + Supabase + Vercel
- Node.js 24.x
- Next.js 16 的 Route 类型系统对动态路径有严格约束，需 `as Route` 断言

## Obsidian 知识库模板

- 单词笔记模板已重写（2026-04-26），新增 5 个 frontmatter 字段
- 模板修正规范在 `Wiki/_模板修正规范.md`
- 1500+ 笔记待批量修正（使用 Trae 工具）
- Dataview 路径已全部从 `VocabVault/Wiki` 修正为 `Wiki`
