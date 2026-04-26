# B0：Raw 字段回填规范

> **用途**：回填 frontmatter 中 `word_root` 和 `network_activation` 两个空/不一致字段
> **目标**：`Wiki/L0_单词集合/`、`Wiki/L0_基础词/`、`Wiki/L0_超纲词/`（共 ~5249 个 .md 文件）
> **前置条件**：上一轮批量修正已完成（phonetic、pos、metaphor_type 已填入）
> **原则**：仅修改 frontmatter，不修改正文任何内容

---

## 一、word_root 回填

### 1.1 提取规则

从正文中提取词根名，写入 frontmatter 的 `word_root` 字段。按以下优先级依次尝试：

**优先级 1：从 wikilink 提取**

在 `## 词根词缀` section 中，查找 `[[词根名|显示名]]` 或 `[[词根名]]` 格式的 wikilink。

```
例1：[[vis-vid|vis]](看，拉丁语 videre) → word_root: vis-vid
例2：[[hab|habit]](持有) → word_root: hab
例3：[[norm]](标准) → word_root: norm
```

**提取词根名部分**（`[[` 和 `|` 或 `]]` 之间的文本），不是显示名。

**优先级 2：从"词源关联"段落推断**

若词根词缀 section 无 wikilink，从"词源关联"段落中提取核心词根名：

```
例：abandon 的词源关联中提到 "bannum（公告），源自原始日耳曼语 *bannan-*"
→ 核心词根是 bandon/bannum，但知识库中无此词根页面
→ word_root: bandon ⚠️（标记待建页面）
```

**优先级 3：前缀词**

若正文"词根词缀"section 分析的是前缀（如 ab-/abs-、de-、inter- 等），且无核心词根：

```
例：abide 的词根词缀 section 分析的是 a-(加强) + bide(等待)
→ 有 wikilink 指向词根？若无，检查 bide 是否有词根页面
→ 无对应页面 → word_root: （留空）
```

### 1.2 验证规则

提取的 `word_root` 值必须满足以下之一：

1. 对应 `Wiki/词根词缀/` 目录下存在的 .md 文件名（不含 .md 后缀）
   - 如 `vis-vid` → `Wiki/词根词缀/vis-vid.md` 存在 ✅
2. 若无对应文件，在值后追加 `⚠️` 标记（表示待建页面）
   - 如 `word_root: bandon ⚠️`
3. 若完全无法提取词根信息，留空：`word_root:`

### 1.3 写入位置

`word_root` 字段已在 frontmatter 中存在（上一轮修正已添加），只需填入或修正值。不改变字段顺序。

### 1.4 示例

**修正前**：
```yaml
word_root: 
```

**修正后（有对应页面）**：
```yaml
word_root: vis-vid
```

**修正后（无对应页面）**：
```yaml
word_root: bandon ⚠️
```

**修正后（无词根信息）**：
```yaml
word_root: 
```

---

## 二、network_activation 回填

### 2.1 回填规则

`network_activation` 字段记录该单词已激活的知识网络类型。按以下规则**程序化判定**，不需要 LLM 语义判断：

| 检查条件 | 激活类型 | 说明 |
|----------|---------|------|
| `word_root` 字段非空 | `词根` | 有词根关联 |
| `## 同义词辨析` section 下有非模板表格行 | `同义辨析` | 表格中除表头和当前词自身外还有其他词 |
| `## 反义词` section 下有非模板列表项 | `反义词群` | 有 `[[xxx]]：...` 格式的反义词条目 |
| `## 派生词链接` section 下有非模板表格行 | `派生词族` | 派生词表格中有实际派生词 |

### 2.2 判定细节

**同义辨析**：
- 表格中必须包含至少 1 个**非当前词**的同义词（用 `[[wikilink]]` 链接）
- 模板占位符（`[[syn1]]`、`...` 等）不算
- 示例：abandon 的同义词表有 desert、forsake、give up、quit → 激活 `同义辨析`

**反义词**：
- 列表中必须包含至少 1 个实际反义词
- 模板占位符（`[[antonym1]]` 等）不算
- 示例：abandon 有 retain、maintain、reclaim → 激活 `反义词群`

**派生词族**：
- 表格中必须包含至少 1 个非当前词自身的派生词
- 模板占位符（`[[derivative1]]` 等）不算
- 示例：abandon 有 abandoned、abandonment、ban → 激活 `派生词族`

### 2.3 格式

```yaml
# 全部激活
network_activation: [词根, 同义辨析, 反义词群, 派生词族]

# 部分激活
network_activation: [同义辨析, 反义词群, 派生词族]

# 无激活
network_activation: []
```

### 2.4 示例

以 abandon 为例：
- `word_root: bandon ⚠️` → 激活 `词根`
- 同义词表有 desert/forsake/give up/quit → 激活 `同义辨析`
- 反义词有 retain/maintain/reclaim → 激活 `反义词群`
- 派生词有 abandoned/abandonment/ban → 激活 `派生词族`

**结果**：`network_activation: [词根, 同义辨析, 反义词群, 派生词族]`

---

## 三、完整修正示例

### 修正前

```yaml
---
title: "abandon"
tags:
  - 学习/英语/词汇
  - 语义场/人体动作
  - 掌握/L0
aliases: []
date: 2026-04-20
mastery: L0
word_freq: 必备词
semantic_field: 人体动作
prototype: 将控制权完全交出
extension_dim: 社会路径
phonetic: "/əˈbændən/"
pos: vt.
metaphor_type: 结构隐喻
word_root: 
network_activation: []
last_review: 2026-04-20
review_count: 0
---
```

### 修正后

```yaml
---
title: "abandon"
tags:
  - 学习/英语/词汇
  - 语义场/人体动作
  - 掌握/L0
aliases: []
date: 2026-04-20
mastery: L0
word_freq: 必备词
semantic_field: 人体动作
prototype: 将控制权完全交出
extension_dim: 社会路径
phonetic: "/əˈbændən/"
pos: vt.
metaphor_type: 结构隐喻
word_root: bandon ⚠️
network_activation: [词根, 同义辨析, 反义词群, 派生词族]
last_review: 2026-04-20
review_count: 0
---
```

---

## 四、输出报告

每批完成后输出：

1. **处理文件数**
2. **word_root 回填统计**：
   - 成功匹配已有词根页面的数量
   - 标记 ⚠️ 待建页面的数量
   - 留空的数量
3. **network_activation 回填统计**：
   - 四种激活类型的命中数
   - 完全为空的数量
4. **待建词根页面清单**（所有标记 ⚠️ 的词根名，去重列表）

---

## 五、注意事项

- **不修改正文**：本次任务仅修改 frontmatter 中的 `word_root` 和 `network_activation` 两个字段
- **不改变字段顺序**：保持现有的 frontmatter 字段顺序不变
- **word_root 的 ⚠️ 标记是临时标记**：后续创建对应词根页面后需移除
- **已有值不覆盖**：如果 `word_root` 或 `network_activation` 已有正确值，不要覆盖
