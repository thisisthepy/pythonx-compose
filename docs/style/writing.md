# Writing style

The house style for thisisthepy documentation. The maintainer named this repository's guide
(`docs/guide/`) as the reference for every repository, so other projects align their READMEs, guides
and docs with what is written here. When this file and the guide disagree, the guide's practice wins
and this file gets corrected.

## Voice

- **Say what is true now.** Describe what the code does today, in the present tense. Something not
  built is marked as such, with its status (`implemented`, `partial`, `planned`) and the issue that
  tracks it. Never describe a plan as if it shipped.
- **Plain and concrete.** No marketing words and no hedging. Name the actual thing: a module, a
  function, a test, an issue number, a commit.
- **Short declarative sentences.** One idea per sentence, about 12 to 18 words on average in English.
  A long sentence is split, not joined with a dash.
- **Reasons beside rules.** When a rule or a limitation is stated, the next clause or sentence gives
  the reason ("because ...", "so that ..."). A reader should never have to guess why.
- **Examples over abstraction.** Show the spelling a user writes (`Modifier.padding(16).fill_max_width()`)
  rather than describing it.

## English and Korean

Every user-facing page exists in both languages (README.md and docs/locale/README_ko.md; each
visible string of the guide in `data-lang="en"` and `data-lang="ko"`).

- **Same content, same order, not word for word.** Each English paragraph has one Korean paragraph
  saying the same thing in natural Korean. A sentence may be split or merged differently, but no
  fact is added or dropped in one language only.
- **Korean register.** User-facing text (README_ko, the guide) uses the polite declarative,
  합니다체: "설치합니다", "동작합니다". Internal records (PROJECT.md, which is written in Korean)
  use the plain declarative, 한다체: "한다", "두었다".
- **Terms.** Code identifiers, Kotlin names, commands and file names stay in their original spelling
  inside code formatting, in both languages. A particle follows code with a space: "`UI.ipynb` 를",
  "`state()` 로". Common technical words are written as Korean loanwords when that is how Korean
  developers say them ("바인더", "스텁", "컴포저블", "모듈"); otherwise the English term stays
  ("snake_case", "wheel", "proxy").
- **Status words** pair one to one: implemented / 구현, partial / 부분, planned / 계획.
- **Headings** are short noun phrases in both languages ("The naming rule" / "이름 규칙").

## Mechanics

- **No em-dash (U+2014)**, anywhere in documents or code. Split the sentence, or use a comma, a colon
  or parentheses. The en-dash in ranges (2023–2024) is fine.
- **Install and run examples use uv, ppp (pypackpack) and tcl (toolchain-lite) only.** No `pip`
  examples. Show uv first: `uv add --prerelease allow pythonx-compose`, then
  `ppp core add "pythonx-compose==0.1.0a2"` and `tcl install pythonx-compose`; run with `uv run ...`.
- **Numbers carry their source.** A test count names the environment it was measured in; a claim
  about upstream names the commit, PR or issue.
- **Links** in README files are absolute (they are read on pypi.org too), and README files never
  link the internal documents (AGENTS.md, PROJECT.md, docs/INTENT.md, docs/SPEC.md).
