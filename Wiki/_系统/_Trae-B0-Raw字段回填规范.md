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

---

## 六、B0 回填校验结果与修正方案（2026-04-26）

### 6.1 校验发现的问题

B0 首轮回填后全库扫描发现三类问题，详见 [[B0回填全库校验报告-2026-04-26]]：

| 问题 | 影响文件数 | 根因 |
|------|-----------|------|
| **A. word_root 为空但 na 含"词根"** | 623 | na 的"词根"判定与 word_root 回填逻辑互相独立 |
| **B. word_root 值不匹配词根目录** | 3808 | 提取逻辑取了正文 wikilink 中的同源词/关联词，而非词根本身 |
| **C. network_activation 过度标记** | ~4400 | 几乎所有文件都被标了"词根"，包括无词根的功能词/复合词 |

### 6.2 word_root 错误提取的四种模式

| 模式 | 示例 | 正确值 |
|------|------|--------|
| 同源词当词根 | receipt → `receive`, imagine → `imitate` | receipt → `cap`/`cap-ceiv-capt` |
| 形近词当词根 | though → `thought` | → 空（功能词无词根） |
| 前缀的派生词当词根 | category → `catastrophe` | → 空 |
| 复合词成分当词根 | workforce → `work` | → 空（复合词非词根派生） |

### 6.3 修正方案：两阶段修正

#### Phase 1：机械修正（可立即执行）

**1a. 修正 Problem A**：623 个文件
```
规则：word_root 为空 → 从 network_activation 移除"词根"
```

**1b. 清空明显错误的 word_root**：约 637 个文件
```
规则：word_root 值满足以下任一条件 → 清空 word_root 并移除 na 中的"词根"：
  - 长度 > 8 且不含连字符（如 "catastrophe", "Akademeia", "bilateral"）
  - 是常见英语完整词且不在词根映射表中（如 "receive", "imitate", "thought"）
例外：复合词根名如 "scrib-script", "pel-puls", "cre-cresc-cret" 应保留
```

**1c. 规范化可映射的 word_root**：206 个文件
```
规则：word_root 值在词根映射表中 → 替换为规范名
映射表来源：
  - 词根目录文件名的连字符拆分（"miss-mit" → mit 映射到 miss-mit）
  - 词根文件 frontmatter 的 aliases 字段
  - 词根文件 title 中的变体名

示例：
  mit → miss-mit
  spec → spec-spect  
  cess → ced-cess
  plic → plic-plex
  vers → ver-vert
  vid → vis-vid
```

#### Phase 2：LLM 重新提取（需 Trae 执行）

对剩余约 2965 个"短词根但无映射"的文件，需 LLM 重新从正文中提取：

```
提取逻辑（改进版）：

1. 读取 ## 词根词缀 section
2. 查找所有 [[target]] wikilink
3. 对每个 wikilink target：
   a. 若 target 在 Wiki/词根词缀/ 目录中存在同名 .md → 这就是词根，使用规范名
   b. 若 target 在 Wiki/词根词缀/ 目录中不存在 → 它可能是：
      - 同源词（如 [[receive]]）→ 忽略，继续找
      - 真正的词根（如 [[mit]]）→ 检查映射表
      - 其他类型页面 → 忽略
4. 若步骤 3 未找到任何词根：
   a. 从构词分析中提取（如 "ad-(=向) + mit(=送)" 中的 mit）
   b. 将提取的形素与映射表对照
5. 若仍无法确定 → word_root 留空

关键改进：
- 优先检查 wikilink target 是否为词根页面，而非盲目取第一个 wikilink
- 区分"同源词链接"和"词根链接"
- 复合词（work+force）、功能词（and, though）、日耳曼本族词（oath）→ 一律留空
```

### 6.4 词根规范化映射表

从词根目录提取的 221 条映射（100 个规范词根名）：

```
# 格式：提取值 → 规范名
# 复合名拆分
mit → miss-mit | miss → miss-mit
spec → spec-spect | spect → spec-spect | spic → spec-spect | spit → spec-spect
cess → ced-cess | ced → ced-cess
plic → plic-plex | plex → plic-plex
dict → (无映射，需新建 dict.md)
...
# 完整映射见 _校验信息/B0回填全库校验报告-2026-04-26.md
```
