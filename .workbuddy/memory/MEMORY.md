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
- B0 回填已执行但质量不佳：word_root 仅 15% 精确匹配词根目录，12% 空值与 na 矛盾，56% 为合法词根形素但无映射
- B0 核心问题：提取逻辑取了正文 wikilink 中的同源词/关联词，而非词根本身
- **B0 Phase 1 机械修正已完成（commit 7ca418d1）**：966 文件修正，Problem A/B 归零
- Phase 1 修正内容：1a(623个na误标词根移除) + 1b(137个长值清空) + 1c(199个映射规范化) + 7个na补词根
- Phase 1 后状态：word_root 匹配词根目录=1009(19%), 空=768(15%), 短词根无映射=3472(66%)
- 修正方案：Phase 1 机械修正已完成 + Phase 2 LLM 重新提取(~3472 文件，待执行)
- 词根规范化映射表：221 条映射，覆盖 100 个规范词根名（从文件名拆分+aliases+title提取）
- Wiki 层（词根/语义场/形近字）质量极不均，需重建
- 重建指令文件在 `Wiki/_系统/_Trae-B{0-4}*.md` 和 `_Trae-Wiki层重建主指令.md`
- 首页 AnimatedCounter 显示 0 是 SSR 快照的客户端组件初始化值，非实际 bug
- 模板/规范文件统一存放在 `Wiki/_系统/` 目录下
- 完备模板已完成（2026-04-27）：L0-L4体系删除、句型标注+语域标签(问题3)、语料三级可信度(问题4)、extension_dim数组化+metaphor_type可选(问题7)
- 复习功能由网站端(vocab-observatory)FSRS管理，Obsidian模板只管内容结构，删除mastery字段和复习记录section
- 批量修正规范已追加第六节（6.1-6.6），含L0-L4删除、数组化、句型回填、语料标记等迁移脚本逻辑

## 技术栈

- vocab-observatory：Next.js 16.2.4 + Turbopack + Supabase + Vercel
- Node.js 24.x
- Next.js 16 的 Route 类型系统对动态路径有严格约束，需 `as Route` 断言

## Obsidian 知识库模板

- 单词笔记模板已重写（2026-04-26），新增 5 个 frontmatter 字段
- 模板修正规范在 `Wiki/_模板修正规范.md`
- 1500+ 笔记待批量修正（使用 Trae 工具）
- Dataview 路径已全部从 `VocabVault/Wiki` 修正为 `Wiki`
