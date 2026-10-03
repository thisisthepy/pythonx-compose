# PROJECT — pythonx-compose

프로젝트 운영에 필요한 핵심 사항을 정리한 문서입니다. 의도는 `docs/INTENT.md`, 동작 계약은
`docs/SPEC.md`, 에이전트 규정은 `AGENTS.md` 에 있습니다.

## 1. 한 줄 요약

Compose(`androidx.compose.*`)를 파이썬에서 쓰기 위한 pip 패키지 **`pythonx-compose`**.
`python-multiplatform` 바인더가 Kotlin 이름 그대로 노출한 Compose 를, 이 저장소의 **실제 파이썬
코드**(`pythonx/`)가 가져와 파이써닉한 구조(`pythonx.compose.*`, `snake_case` 매개변수,
확장 함수 = 메서드)로 재구성한다.

## 2. 사양의 출처

| 우선순위 | 무엇 | 비고 |
|---|---|---|
| 1 | 사용자 발언 | `docs/INTENT.md` 에 원문 인용 |
| 2 | `UI.ipynb` | 메인 체크아웃에만 있음. git-ignore 됨. **복사·이동·추가 금지** |
| 3 | `docs/INTENT.md` → `docs/SPEC.md` | 사양에서 파생된 문서. 어긋나면 1·2 가 이긴다 |

노트북의 함수 시그니처는 **이름 예시**다. 실제 규칙은 "Kotlin 원래 매개변수를 `snake_case` 로
노출한다" 이다 (`onclick` 이 아니라 `on_click`).

## 3. 현황 (2026-10-03)

`docs/SPEC.md` 기준. 구현 = 이 저장소의 코드 + 읽고 통과를 확인한 테스트가 있는 것.

| 상태 | 항목 |
|---|---|
| 구현 | 매핑 매니페스트 `pythonx-map.toml`, `@Composable` 항등 데코레이터, 실제 디스크 패키지 `pythonx` 와 모듈 수준 규칙 기반 재노출(snake_case 이름·키워드·시그니처, 오버로드 디스패치, 값 클래스 허용 목록), 실제 Compose 1.11.1 에서 생성한 `.pyi` 스텁과 `py.typed`(wheel 포함, mypy 로 검사), `Alignment`/`Arrangement` 상수(평면 `Alignment.End` 와 묶음 `Alignment.Horizontal.End` 모두, #9), proxy 메서드의 snake_case 키워드 인자(`m.padding(padding_values=...)`, python-multiplatform `describe_member` 필요; Kotlin 이름도 실행 시 그대로 통하고 스텁은 snake_case 만) |
| 부분 | 선언형 앱 루트 `@app`·`state`·`app_root`(#11; 로직은 테스트됨, 바인더 경로는 #38 모양의 가짜 호스트로 테스트됨, 실제 Compose 증거는 E2E 모듈 #19; 숫자·문자열 상태는 python-multiplatform #69 부터 왕복됨), 배포 설정, Material 3 위젯(렌더 증거는 python-multiplatform 에만), `Icon`(import 만 됨)·`DefaultIcons`(`Icons.Default` alias, 가짜 호스트로만 테스트됨, 스텁에서는 `DefaultIcons.Add` 가 `ImageVector`; `DefaultIcons.Add` 로 쓴다 — 노트북의 `DefaultIcons.Add()` 가 아님), `TextField(state=...)`·`TextFieldState`(#10; `pythonx.compose.foundation.text.input`, 가짜 호스트로 테스트됨, 노트북의 `text_state=`/`padding=` 는 `state=`/`modifier=Modifier.padding(8)`; IME 조합 증거는 python-multiplatform E2E #26) |
| 계획 | `remember_saveable`·색 스킴·코루틴 스코프 |

### 테스트 기준선

```
python3 -m pytest tests -q
  PythonMultiplatform 체크아웃 없음       140 passed, 112 skipped
  python-multiplatform develop 31c092f0+    251 passed, 1 skipped
  describe_member 없는 체크아웃             같은 수, 그중 7 개 건너뜀  (python-multiplatform #54 이전)
  describe(module, name) 없는 체크아웃      같은 수, 그중 13 개 건너뜀  (python-multiplatform #36 이전)
  그보다 오래된 체크아웃                    거기에 5 개 더 건너뜀  (member resolver 없음)
```

`describe_member`(python-multiplatform #54)가 없는 바인더에서는 메서드 키워드를 확인하는 7 개가(Kotlin 키워드로 되돌아가는 2 개는 실행됨), `describe(module, name)`(python-multiplatform #36)이 없는 바인더에서는 묶음 상수를 확인하는 13 개가,
member resolver(python-multiplatform `ba4c6f49`)가 없는 바인더에서는 proxy 의 snake_case 메서드를 부르는
5 개가 더 건너뛴다. 두 환경 모두의 건너뜀 1 개는 worktree 에 없는 `UI.ipynb` 의 테스트다. 건너뜀은 통과가 아니다.
체크아웃 없이 통과하는 134 개 중 61 개는 타입 스텁과 wheel 을 검사하고(SPEC S1.2), 나머지 다수는 *부재*(옛 토큰·삭제된
파일이 없음)를 확인하는 것이라 기능 진척으로 세지 않는다.

### 마일스톤

GitHub 마일스톤과 같은 내용이다. 날짜는 2026-10-03 에 정했고, 같은 날 M2·M3 를 1주 앞당겼다(아래 M2 근거).

| 마일스톤 | 목표일 | 범위 | 완료 기준 | 이슈 |
|---|---|---|---|---|
| M1 실제 `pythonx` 패키지와 규칙 기반 재노출 | 2026-10-16 | SPEC §3, S4.1, S6 | 실패 37개 통과(체크아웃 있을 때), 가짜 `pythonx` 를 전제한 테스트 없음, 규칙을 끄면 테스트가 실패 | #7, #8 |
| M2 `UI.ipynb` 위젯 동작 | 2026-11-06 | SPEC S5.2, S5.3, §7, §8, INTENT §5 | 노트북이 쓰는 위젯마다 PythonMultiplatform 렌더 증거, TextField 의 IME 조합 보존, 선언형 앱 루트(갱신 함수 없음)로 셀에서 다시 정의한 화면이 반영됨 | #9, #10, #11 |
| M3 pip 설치 가능한 `pythonx-compose` | 2026-11-20 | SPEC S1.1, S1.2 | wheel 을 빌드해 `.pyi`·`py.typed`·`pythonx-map.toml` 이 들어 있음을 확인하는 테스트, 스텁과 런타임 시그니처 일치 | #12, #13 |

날짜 근거:

- **M1 (2주):** 바인더 계약(`inspect.signature`, `python_multiplatform.describe`)이 PythonMultiplatform `d00f413f` 에 착지했다. 남은 일은 이 저장소의 순수 Python 과 가짜 호스트 하네스뿐이라 JVM 빌드가 필요 없다.
- **M2 (M1 뒤 3주):** 위젯마다 JVM 렌더 테스트가 필요하다. 처음엔 Gradle 캐시 링크가 끊겼다고 보고 4주로 잡았으나, 캐시는 `PythonMultiplatform/.caches` 로 다시 걸려 Compose 픽스처가 통과하고 있었고, 노트북 관련 질문도 INTENT §5 로 결정됐다. 남은 위험은 `TextField(state=...)` 의 IME 조합 증거(python-multiplatform E2E #26)와, 앱 루트 교체를 Kotlin 컴포지션이 관찰하는 진입점(바인더 몫일 수 있음)이다.
- **M3 (M2 뒤 2주):** 스텁은 M1 규칙만 있으면 만들 수 있어 M2 와 겹쳐 진행할 수 있다. 다만 노트북 위젯의 최종 이름이 M2 에서 정해지므로 마감은 M2 뒤로 둔다.

## 4. 구조

```
pythonx/compose/          import 패키지 (현재 대부분 독스트링만 있는 모듈)
  runtime/                @Composable
  pythonx-map.toml        pythonx ↔ androidx 매핑 매니페스트 (wheel 에 함께 실림)
  _reexport.py            매니페스트 모듈 전체에 적용되는 재노출 규칙 하나
  ui/                     modifier.py (빈 Modifier 등록 지점), alignment.py
  layout/                 arrangement.py
  material3/              __init__.py 하나 (위젯은 모두 재노출 규칙으로)
scripts/                  gen_stubs.py (스텁 생성기, wheel 에 싣지 않음)
tests/                    pytest (unittest 스타일), 유일한 테스트 폴더
docs/INTENT.md  docs/SPEC.md  docs/locale/  docs/guide/
.github/workflows/        CI
.github/scripts/          check_guide.py (tests/test_guide.py 가 실행), release/ (CI 전용)
```

## 5. 빌드·테스트

```bash
python3 -m pytest tests -q                       # 파이썬 테스트
PYTHONMULTIPLATFORM_HOME=<checkout> python3 -m pytest tests -q   # 바인더 계층 포함
python3 .github/scripts/check_guide.py           # 가이드: HTML 파싱, 링크, en/ko 짝 (tests/test_guide.py 도 실행)
```

- pytest 가 없으면 `.tmp/` 아래에 가상환경을 만든다 (홈 디렉터리 금지).
- `PythonMultiplatform` 은 읽기 전용이다.
- wheel 빌드 후 내용물 확인은 아직 자동화되어 있지 않다.

## 6. 결정된 것

- 배포 이름은 `pythonx-compose`.
- `pythonx` 는 디스크에 존재하는 실제 패키지이고, 그 코드가 `androidx` 모듈을 가져와 재구성한다.
- 바인더(`python-multiplatform`)는 Kotlin 네임스페이스를 절대 바꾸지 않는다. `androidx → pythonx`
  매핑은 이 저장소의 일이고, `pythonx-map.toml` 이 그 매니페스트다.
- Kotlin 확장 함수는 수신 객체 프록시의 메서드로 보인다.
- `@Composable` 데코레이터는 유지한다.
- `.pyi` 스텁은 패키지에 포함되어 배포된다.
- 런타임 리플렉션(chaquopy `jclass`, JPype, 맹글링된 JVM 이름 검색)은 쓰지 않는다.

## 7. 열린 질문 (메인테이너 결정 필요)

1. **코루틴 스코프** — 노트북이 import 하는 `DefaultCoroutineScope`·`MainCoroutineScope`.
2. **`pythonx-map.toml` 의 이중 표기** — `pythonx.compose.layout` 과
   `pythonx.compose.foundation.layout` 를 둘 다 유지할지.
3. **릴리스·Pages 활성화** — `.github/scripts/release/` 와 `.github/workflows/`(release-sync, pages)는
   들어와 있다. main 보호는 메인테이너가 저장소 설정에서 직접 관리하며 main 은 잠겨 있다. 스크립트나
   에이전트는 보호 설정을 만들거나 바꾸지 않는다. release→main PR 머지는 메인테이너가 한다.

### 결정됨 (2026-10-03, #60)

- **저장소 정리.** `test/`(2023–2024 샘플), `pythonx/compose/lite/`(은퇴한 JPype 프로토타입),
  서브모듈 `pythonx/compose/native`(→ thisisthepy/swing-graalvm-demo @ 090f0190)는 삭제했고,
  태그 `archive/pre-restructure` 로 되찾을 수 있다. `tools/` 는 없앴다: 스텁 생성기는
  `scripts/`(메인테이너 승인), 가이드 검사기와 릴리스 스크립트는 `.github/scripts/`.

### 결정됨 (2026-10-03, #62) — 첫 PyPI 릴리스

- 워크플로 이름: `tests.yml` → `test.yml`, PyPI 배포는 `publish-pypi.yml`.
- 첫 버전은 `0.1.0a1`(알파, 프리릴리스). PyPI 메타데이터(설명·README·MIT·저자·URL·분류자)는 채웠고,
  README 의 링크는 pypi.org 에서 열리도록 절대 URL 이다(`main` 링크는 `main` 이 `develop` 을 따라잡은 뒤에 열린다).
- 배포 방법: 릴리스할 커밋에 태그 `v0.1.0a1` 로 GitHub Release 를 게시하면(알파는 pre-release 표시)
  `publish-pypi.yml` 이 Release 태그와 `pyproject.toml` 버전을 대조하고, sdist·wheel 을 빌드하고,
  `twine check`·새 venv 스모크를 거쳐 트러스티드 퍼블리싱으로 올린다. 태그만 푸시해서는 아무것도
  올라가지 않는다(같은 버전은 PyPI 에 다시 올릴 수 없으므로 의도적인 단계로 둠). **현황: 0.1.0a1 배포됨**(2026-10-03, develop `134a641` 에서 pre-release
  `v0.1.0a1`, publish-pypi run 37120641414; https://pypi.org/project/pythonx-compose/). 새 venv 에서
  `pip install pythonx-compose==0.1.0a1` 후 import 스모크 통과.

### 결정됨 (2026-10-03, `docs/INTENT.md` §5)

- **선언형 앱 루트, 갱신 함수 없음.** 노트북의 `main.App.update(...)`·`getValue()`/`setValue()` 는
  당시 구현의 제약이었다. 루트는 선언하고 다시 정의하면 화면이 따라가며, 상태는 Compose 상태 모델을
  따른다(#11).
- **`Column`·`Row`·`Spacer`** 는 `pythonx.compose.material3` 와 `pythonx.compose.layout` 양쪽에서
  import 된다.
- **정렬 상수** 는 `Alignment.End` 와 `Alignment.Horizontal.End` 둘 다 지원한다.
- 소문자 `modifier` 는 두지 않는다(`Modifier` 로 쓴다). ARGB 정수 색은 받지 않는다
  (`Color(0xFFFF0000)`). `Spacer(start=...)` 는 지원하지 않는다(`Modifier.padding`). `DefaultIcons` 는
  `Icons.Default` 의 alias(매니페스트 `[aliases]` 의 `{ DefaultIcons = "Icons.Default" }`, 읽을 때마다 해석). — `docs/INTENT.md` §5.4–5.7
- 합성된 `pythonx` 를 전제한 테스트·독스트링은 #7 에서 정리했다.

## 8. 관련 저장소

| 저장소 | 관계 |
|---|---|
| `python-multiplatform` | 바인더. 이 패키지가 런타임에 의존하는 대상. 이 저장소에서는 읽기 전용 |
| `toolchain` | Gradle 빌드 플러그인 |
| `pypackpack` | 파이썬 프로젝트 배포 |
| `torchnative`, `Gemstone` | 같은 생태계의 다른 프로젝트 |
