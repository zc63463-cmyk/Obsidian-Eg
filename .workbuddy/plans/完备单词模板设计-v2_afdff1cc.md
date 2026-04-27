---
name: 完备单词模板设计-v2
overview: 聚焦内容结构的完备单词模板，解决问题3/4/7。复习交给网站端，frontmatter 保留 mastery+review_count 作本地简单标记，不加FSRS。
todos:
  - id: write-template
    content: 编写完备模板文件 _模板-单词笔记.md（正文所有 section 填写指南 + 句型符号定义表）
    status: completed
  - id: update-dim-ref
    content: 更新 _延伸维度与隐喻类型参考.md：extension_dim 数组化 + metaphor_type 可选
    status: completed
    dependencies:
      - write-template
  - id: update-revision-doc
    content: 更新 _模板修订方案-句型与语料.md：追加完备模板变更摘要
    status: completed
    dependencies:
      - write-template
  - id: update-correction-spec
    content: 更新 _模板修正规范.md：追加 extension_dim 数组化、句型标注回填、语料可信度标记修正项
    status: completed
    dependencies:
      - write-template
  - id: write-sample
    content: 用完备模板重写 abandon.md 作为示范卡
    status: completed
    dependencies:
      - write-template
---

## 用户需求

重新设计完备的英语单词笔记模板，系统性解决三个已确认问题：

- **问题3（句型框架）**：核心释义嵌入句型标注 + 语域标签，搭配改语块格式，常见错误 callout
- **问题4（语料可信度）**：三级可信度标记（[真题]/[COCA]/[例]），完整句子格式
- **问题7（维度框架）**：extension_dim 改多值数组，metaphor_type 降级为可选

## 关键约束

- **L0-L4 等级体系全部删除**：删除 frontmatter 的 `mastery` 字段、`- 掌握/L0` tag、所有 callout 标题的 `· Ln` 后缀、复习记录的"当前等级"行。掌握度完全由网站端 FSRS 算法管理
- **Frontmatter 不加复习字段**：不加 FSRS 字段，复习功能完全交给网站端（vercel+supabase）
- **复习记录 section 删除**：网站端管复习，Obsidian 不需要此 section
- **主动产出 section 保留**：作为个人笔记区，但简化格式
- 5+3 维度框架（5延伸维度+3隐喻类型）确认够用，子标题无限扩展

## 核心特性

- 核心释义嵌入句型标注 `V N` + 可选语域标签 `[formal]`
- 搭配 section 定位为高频语块（lexical chunks），不再重复句型
- 语料三级可信度，完整句子，核心搭配粗体
- extension_dim 改 YAML 数组支持多值，metaphor_type 可选
- 每个字段和 section 附填写指南，消除占位符歧义

## 技术栈

- 文件格式：Obsidian Markdown + YAML frontmatter
- 参考框架：Lakoff & Johnson 隐喻理论（3类型）、5维延伸维度、Hunston & Francis Pattern Grammar
- 句型符号体系：V/N/that-clause/V-ing/to V/oneself to N/prep N 等（学习者友好简写）

## 实现方案

### Frontmatter 字段

**删除字段**：`mastery`（L0-L4 等级由网站端 FSRS 管理）

**删除 tag**：`- 掌握/<mastery_level>`（与 mastery 重复）

**保留字段**：title, tags(去掉掌握tag), aliases, date, word_freq, phonetic, pos, semantic_field, prototype, extension_dim, metaphor_type, word_root, network_activation, last_review, review_count

**两处格式调整**（不改字段名和含义）：

- `extension_dim: 社会路径` → `extension_dim: [社会路径]`（YAML 数组，支持多值如 `[社会路径, 具身路径]`）
- `metaphor_type` 降级为可选（无隐喻则整行删除，不报错）

### 正文 Section 设计

**核心释义**（问题3核心）：义项后加句型标注 + 可选语域标签

```markdown
**vt.** ①==**抛弃，放弃**== `V N` [formal] ；②==**沉溺于**== `V oneself to N` [literary] ；
```

语域标签可选值：formal / informal / law / academic / literary / spoken / written / journalism

**常见错误 callout**（可选，紧跟核心释义）：

```markdown
> [!warning]- 常见错误
> suggest 不接 `to V`：~~suggest to go~~ → suggest going / suggest that we go
```

**搭配与短语**（问题3）：纯语块格式，含使用场景/语域（去掉 `· L3` 后缀）

```markdown
> [!example]- 搭配
> - **abandon ship**：弃船（紧急命令）
> - **with reckless abandon**：不顾一切地（文学/状语语块）
```

**真题/语料关联**（问题4）：三级可信度 + 完整句子（去掉 `· L3` 后缀）

```markdown
> [!example]- 语料
> - The government abandoned the project due to budget constraints. `[真题]`
> - She danced with wild abandon, as if no one was watching. `[例]`
```

可信度分级：[真题]=试卷原文 / [COCA-ACAD]/[BNC-SPOKEN]=语料库 / [例]=AI生成或自编

**复习记录**：**整个 section 删除**，复习由网站端 FSRS 管理

**主动产出**：保留作为个人笔记区，简化格式

```markdown
> [!success]- 主动产出
> **写作用例**：<自己在写作/翻译中使用该词的例句>
> **翻译实践**：<翻译练习中的使用记录>
```

### 延伸维度参考文件更新

`_延伸维度与隐喻类型参考.md` 使用规则更新：

- 第1条改为"可多选（YAML 数组格式）"
- 第2条改为"metaphor_type 可选，无隐喻时不填"

## 目录结构

```
Wiki/_系统/
├── _模板-单词笔记.md              # [MODIFY] 完备模板主文件，含所有 section 的填写指南
├── _延伸维度与隐喻类型参考.md      # [MODIFY] 更新 extension_dim 多值数组说明和 metaphor_type 可选说明
├── _模板修订方案-句型与语料.md     # [MODIFY] 追加完备模板变更摘要（移除FSRS相关内容）
└── _模板修正规范.md               # [MODIFY] 追加批量修正项：extension_dim 数组化、句型标注回填、语料可信度标记

Wiki/L0_单词集合/
└── abandon.md                     # [MODIFY] 用完备模板重写作为示范卡
```

## 实现要点

- **删除 L0-L4 体系**：删除 frontmatter 的 mastery 字段、`- 掌握/L0` tag、所有 callout 的 `· Ln` 后缀、复习记录 section
- 复习由网站端 FSRS 负责，Obsidian 模板只管内容结构
- 语域标签可选不强制，大部分词不需要标
- extension_dim 数组格式：`extension_dim: [社会路径, 具身路径]`
- 现有 5249 卡片的迁移策略：`extension_dim` 单值 → 包裹为数组，`mastery: L0` 删除，`- 掌握/L0` tag 删除，callout `· Ln` 后缀删除，复习记录 section 删除
- 逐行解析 frontmatter（不用正则 \s*），避免 B0 脚本跨行匹配 bug
- 句型符号定义表写入模板文件注释区，供批量回填时参考
- 语料可信度标记由 LLM 批量判断并追加，片段型语料需重写为完整句子