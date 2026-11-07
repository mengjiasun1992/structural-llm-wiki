# 繁體中文

Traditional Chinese (zh-Hant), in Taiwan usage: the headings and labels of a
narrative written in it, and how to write it.

## Headings

| English | Translation |
|---|---|
| Abstract | 摘要 |
| Terminology | 術語 |
| Appendix | 附錄 |
| Glossary | 詞彙表 |
| SMEs | 領域專家 |
| References | 參考資料 |
| Sources read | 已讀來源 |
| Citations | 引用 |
| Metadata | 中繼資料 |
| Context | 背景 |
| The problem | 問題 |
| What happened | 經過 |
| Why | 原因 |
| The ideas at work | 背後的原理 |
| Outcome | 結果 |
| Lessons | 經驗教訓 |
| Where to go next | 延伸閱讀 |
| The choices | 候選方案 |
| When to choose which | 如何選擇 |
| At a glance | 一覽 |
| Dimensions to think through | 考量面向 |
| Pitfalls | 常見陷阱 |
| Overview | 概覽 |
| Definition | 定義 |
| In short | 簡而言之 |
| Precisely | 精確定義 |
| Key ideas | 核心要點 |
| Boundaries | 邊界 |
| The map | 全景圖 |
| The main items | 主要內容 |
| Tensions and trade-offs | 張力與取捨 |
| Classic case studies | 經典案例 |
| Applying them | 實際應用 |
| Background | 背景知識 |
| The core idea | 核心概念 |
| How does it work? | 它是如何運作的？ |
| Variants | 變體 |
| Design decisions and trade-offs | 設計決策與取捨 |
| Limitations and failure modes | 侷限與失效模式 |
| Misconceptions | 常見誤解 |

## Labels

| English | Translation |
|---|---|
| (optional) | （選填） |
| Key takeaways | 要點 |
| Term | 術語 |
| Person | 人員 |
| Why them | 理由 |
| Ask them | 可以請教的問題 |
| Dimension | 面向 |
| Figure | 圖 |
| Our own reasoning, after a statement or on a section's heading: a conclusion, comparison or example no cited source states. | 我們自己的推論，標在陳述之後或章節標題上：引用的來源中沒有的結論、比較或例子。 |
| A gap, after a statement or on a heading: something the question needs that the sources don't answer. | 缺口，標在陳述之後或標題上：問題需要、而來源沒有回答的內容。 |

## Book

| English | Translation |
|---|---|
| Contents | 目錄 |
| About this book | 關於本書 |
| See also | 另見 |
| Appendix A: Sources | 附錄 A：來源 |
| Appendix B: Glossary | 附錄 B：詞彙表 |
| Appendix C: Open questions | 附錄 C：待解問題 |
| Version | 版本 |
| Date | 日期 |
| Commit | 提交 |
| License | 授權條款 |
| Published | 發布日期 |
| Cited by | 引用於 |
| Known issues | 已知問題 |
| {n} min read | 閱讀約 {n} 分鐘 |
| {n} min | {n} 分鐘 |
| Original | 原文 |
| The narratives in this book are the wiki owner's work. Every source belongs to its authors: the book links to it and quotes it briefly, but never copies it. | 本書中的敘述是 wiki 擁有者的作品。每個來源都屬於其作者：本書連結到來源並簡短引用，但從不複製。 |
| The narratives were written by an LLM and reviewed by the owner. | 這些敘述由大型語言模型撰寫，並經擁有者審閱。 |
| This book is a snapshot of the wiki at the commit on its cover. | 本書是 wiki 在封面所示提交時的快照。 |
| A number in brackets, such as [3], is a citation: it links to the source's entry in Appendix A, which links to the original. | 方括號中的數字（如 [3]）是引用：它連結到附錄 A 中該來源的條目，條目再連結到原文。 |
| Made by {tool} and {models}, from {source}. | 由 {tool} 與 {models} 根據 {source} 製作。 |
| Made by {tool}, from {source}. | 由 {tool} 根據 {source} 製作。 |

## Release

| English | Translation |
|---|---|
| Released while these checks failed: | 發布時以下檢查未通過： |
| Since | 自 |
| First release | 首次發布 |
| narratives | 篇敘述 |
| sources | 個來源 |
| New narratives | 新增敘述 |
| Updated narratives | 更新的敘述 |
| Removed narratives | 刪除的敘述 |
| New sources | 新增來源 |
| Nothing in the wiki changed since the last release. | 自上次發布以來，wiki 沒有變化。 |
| Open questions | 待解問題 |
| Book | 書 |
| none: turn a format on in Config.toml's [structural-llm-wiki-release] | 無：在 Config.toml 的 [structural-llm-wiki-release] 中開啟一種格式 |

## Writing

- **Register:** plain written Chinese for an engineer (書面語), in Traditional characters and Taiwan usage (程式、資料、網路、軟體, not 程序、数据、网络、软件), short sentences, no slang and no filler such as 值得注意的是 or 眾所周知.
- **Terms:** on first use, the Chinese term with the English in full-width brackets, 一致性雜湊（consistent hashing）, then the Chinese term alone, the same one every time. A term with no settled Chinese translation stays English. Code, commands, file names and API names stay as written.
- **Punctuation:** full-width in Chinese text, ，。：；？！（）, with 「」 for quotation marks (『』 inside them) and 《》 for the title of a paper or book; half-width in code, formulas and numbers.
- **Spacing:** a space between Chinese and a Latin word or a number (使用 3 個副本，每個 key 一個), none next to full-width punctuation.
- **Citations and markers:** inside the sentence, before its full stop, after a space: 鍵只會移動到相鄰節點 [3]。 A marker the same: 這是我們的推論 [→]。
- **Quotations:** a quotation from a source in another language keeps its words, in 「」, with its translation after it in full-width brackets: 「each node is assigned a random position」（每個節點被分配一個隨機位置）[2]。
- **Numbers:** Arabic numerals, with the source's units.
