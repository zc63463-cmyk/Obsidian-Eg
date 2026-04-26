# B4：形近字页面生成规范

> **用途**：从零生成 `Wiki/形近词/` 目录下的形近字辨析页面
> **目标**：生成约 50-80 个形近字辨析页面
> **前置条件**：B0 已完成（word_root 回填完毕）
> **当前状态**：目录下仅有 `_模板-形近词笔记.md`，无任何实际内容页面

---

## 一、形近字判定逻辑

这是最需要明确规则的部分——什么算形近字，什么不算。

### 1.1 判定为形近字的条件（满足任一即可）

| 类型 | 定义 | 示例 | 优先级 |
|------|------|------|--------|
| **前缀/后缀互换** | 相同词根 + 不同前缀/后缀，导致词义不同 | adapt/adopt/adept, affect/effect, insure/ensure | 最高 |
| **词根变体** | 同源词根的不同变体形式 | spec/spect/spic, ceive/cept/cip | 高 |
| **拼写高度相似** | 编辑距离 ≤ 2，且非上述两类 | complement/compliment, principal/principle | 中 |
| **音近误混** | 发音相似导致常被混淆 | weather/whether, stationary/stationery | 低 |

### 1.2 不判定为形近字的情况

| 排除规则 | 说明 | 反例 |
|----------|------|------|
| 仅有共同前缀 | 共享前缀但词根完全不同 | abandon/absorb（只是都含 ab-，词根不同） |
| 仅有共同后缀 | 共享后缀但词根完全不同 | adaptation/information（只是都含 -tion） |
| 词长差距 > 3 | 长度差异过大不易混淆 | ab/description |
| 词频均超纲 | 两个词都不在考研/四六级范围内 | 仅作参考，不绝对排除 |

### 1.3 编辑距离计算参考

对 5249 个单词两两计算 Levenshtein 编辑距离，筛选出编辑距离 ≤ 2 的词对。然后按上述规则过滤掉假阳性。

**注意**：编辑距离只是初筛工具，不是最终判定标准。很多编辑距离为 1 的词对（如 able/abide）并不算形近字，因为它们的词源和含义完全无关。

---

## 二、聚类规则

### 2.1 小群组（2-4 个词）

最常见的情况。按以下规则确定组名：

- **若有共同词根**：用"词根名"作为组名
  - 如 adapt/adopt/adept → 组名"adapt-adopt-adept"
- **若无共同词根**：用"词1/词2/词3"格式
  - 如 complement/compliment → 组名"complement-compliment"

### 2.2 大群组（5+ 个词）

如 -sist 系列（assist/exist/insist/persist/resist/consist），需要按语义子群分组。

- 组名用"词根系列"格式："-sist系列"
- 页面内按语义子群分节

---

## 三、页面格式

### 3.1 小群组格式（2-4 个词）

```markdown
---
title: "adapt / adopt / adept"
tags:
  - 学习/英语/词汇/形近词
  - 语义场/人本世界
aliases: []
date: 2026-04-26
---

# adapt / adopt / adept

> [!info] 形近辨析
> 以下单词在拼写上相近，注意区分

## 形近词对比

| 词 | 词源 | 核心义 | 拼写差异 | 记忆锚点 |
|----|------|--------|---------|---------|
| [[adapt]] | ad-(向) + apt(适合) | 适应，改编 | **a**dapt → **a**pt(适合) | **a** 适应 **a**pt（适合）|
| [[adopt]] | ad-(向) + opt(选择) | 采纳，收养 | ad**o**pt → **o**pt(选择) | **o** 采纳 **o**pt（选择）|
| [[adept]] | ad-(向) + ept(掌握) | 熟练的，内行的 | ade**pt** → e**pt**(掌握) | ade**pt** = ex**pert**（专家）|

## 故事会

> [!tip] 故事串联记忆
> 一个 **adept**（熟练的）翻译家，能快速 **adapt**（适应）不同风格的文本，因为他 **adopt**（采纳）了最有效的翻译策略——**熟练**的人**适应**变化，靠的是**采纳**好方法。
```

### 3.2 大群组格式（5+ 个词）

```markdown
---
title: "-sist 系列"
tags:
  - 学习/英语/词汇/形近词
  - 语义场/人本世界
aliases: []
date: 2026-04-26
---

# -sist 系列

> [!info] 形近辨析
> 以下单词共享词根 sist-（站立），前缀不同导致含义分化

## 词根核心

[[sist|st-/sta-/sist-]]（站立）—— 所有 -sist 词的核心画面都是"站在某个位置"，前缀决定了"站在哪里"。

## 全局对比

| 词 | 构词分析 | 核心义 | "站在哪" |
|----|---------|--------|---------|
| [[assist]] | as-(向) + sist(站) | 协助 | 站**在旁边**帮忙 |
| [[consist]] | con-(共同) + sist(站) | 组成 | 站**在一起**构成整体 |
| [[exist]] | ex-(出来) + sist(站) | 存在 | 站**出来**显现 |
| [[insist]] | in-(在上) + sist(站) | 坚持 | 站**在上面**不动摇 |
| [[persist]] | per-(贯穿) + sist(站) | 持续 | 站**到底**不放弃 |
| [[resist]] | re-(对抗) + sist(站) | 抵抗 | 站**在对立面**对抗 |

## 故事会

> [!tip] 故事串联记忆
> 想象一个团队：有人**assist**（站在旁边帮忙），有人**insist**（站在上面坚持己见），有人**persist**（站到底持续努力），有人**resist**（站在对立面抵抗）。他们**consist**（站在一起组成团队），为了让一个想法**exist**（站出来成为现实）。一个 -sist，六种立场。
```

---

## 四、数据提取规则

### 4.1 从单词卡提取

对每个形近字组，需要从各词的 raw 卡中提取：

| 提取项 | 来源 section | 用途 |
|--------|-------------|------|
| 词源/构词分析 | `## 词根词缀` | 填入"词源"和"构词分析"列 |
| 核心义 | `## 核心释义` 中加 ==== 高亮的释义 | 填入"核心义"列 |
| 原型义 | `> [!tip] 原型义` | 构建故事串联记忆 |
| 语义场 | frontmatter `semantic_field` | 填入页面 tags |
| 记忆锚点 | `## 记忆锚点` | 辅助构建"记忆锚点"列 |

### 4.2 故事串联记忆构建规则

1. 用中文故事将形近词串联起来
2. 故事必须包含每个词的核心义
3. 优先利用"原型义"构建故事画面
4. 故事要有场景感和画面感，不要干巴巴的列举
5. 每个词在故事中的出现要自然，不要生硬嵌入
6. 故事长度控制在 3-5 句

---

## 五、预判的高频形近字组

以下是根据考研/四六级词汇经验预判的常见形近字组，供优先处理：

### 5.1 前缀/后缀互换型（最高优先级）

| 组 | 词 |
|----|----|
| adapt/adopt/adept | adapt(适应) / adopt(采纳) / adept(熟练) |
| affect/effect | affect(影响v) / effect(效果n) |
| assure/ensure/insure | assure(保证) / ensure(确保) / insure(保险) |
| continual/continuous | continual(频繁的) / continuous(连续的) |
| conserve/preserve/reserve | conserve(保存) / preserve(保护) / reserve(预留) |
| complement/compliment | complement(补充) / compliment(赞美) |
| principal/principle | principal(主要的/校长) / principle(原则) |
| stationary/stationery | stationary(静止的) / stationery(文具) |
| economic/economical | economic(经济的) / economical(节约的) |
| historic/historical | historic(有历史意义的) / historical(历史的) |
| sensible/sensitive | sensible(明智的) / sensitive(敏感的) |
| considerate/considerable | considerate(体贴的) / considerable(大量的) |
| respectable/respectful/respective | respectable(值得尊敬的) / respectful(恭敬的) / respective(各自的) |
| rise/arise/raise/arouse | rise(上升vi) / arise(出现vi) / raise(举起vt) / arouse(唤醒vt) |

### 5.2 拼写相似型

| 组 | 词 |
|----|----|
| abroad/aboard | abroad(在国外) / aboard(在船上) |
| accept/except/concept | accept(接受) / except(除了) / concept(概念) |
| acquire/inquire/require | acquire(获取) / inquire(询问) / require(要求) |
| alive/live/living/lively | alive(活着的) / live(现场) / living(生计) / lively(活泼的) |
| area/era | area(区域) / era(时代) |
| award/reward | award(授予) / reward(奖赏) |
| collar/cellar/scholar | collar(领子) / cellar(地下室) / scholar(学者) |
| contend/content/context/contest | contend(竞争) / content(内容/满足) / context(语境) / contest(竞赛) |
| desert/dessert | desert(沙漠/抛弃) / dessert(甜点) |
| emerge/immerge | emerge(出现) / immerge(浸入) |
| expand/expend | expand(扩展) / expend(花费) |
| extend/extent | extend(延伸v) / extent(程度n) |
| industrial/industrious | industrial(工业的) / industrious(勤奋的) |
| later/latter | later(后来) / latter(后者的) |
| personal/personnel | personal(个人的) / personnel(人事) |
| status/statue/statute | status(地位) / statue(雕像) / statute(法规) |
| wander/wonder | wander(漫游) / wonder(想知道) |

---

## 六、执行方式

### 6.1 阶段一：扫描聚类（可脚本化）

1. 收集全部 5249 个单词名
2. 计算两两编辑距离，筛选 ≤ 2 的词对
3. 按"一、形近字判定逻辑"过滤假阳性
4. 将剩余词对聚类为词组
5. 输出词组清单供人工审核

### 6.2 阶段二：页面生成（需 Trae）

1. 按照审核后的词组清单，逐组生成页面
2. 每组从各词的 raw 卡中提取数据
3. 按照第三节的页面格式生成
4. 确保所有 `[[wikilink]]` 指向知识库中存在的页面

### 6.3 阶段三：交叉验证

1. 检查每个形近字页面中的 wikilink 是否都指向实际存在的单词卡
2. 检查单词卡是否需要新增 `confusable_group` 相关的 frontmatter 引用
3. 检查是否有遗漏的形近字组

---

## 七、输出报告

1. 扫描聚类结果：总词对数、过滤后词对数、最终词组数
2. 每个形近字页面的文件名和包含的词
3. 无法归类的边缘词对（需人工判定）
4. 发现的知识库中缺失的词条（形近组中某词不在库中）
