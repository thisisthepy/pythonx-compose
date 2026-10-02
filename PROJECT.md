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

## 3. 현황 (2026-10-02)

`docs/SPEC.md` 기준. 구현 = 이 저장소의 코드 + 읽고 통과를 확인한 테스트가 있는 것.

| 상태 | 항목 |
|---|---|
| 구현 | 매핑 매니페스트 `pythonx-map.toml`, `@Composable` 항등 데코레이터 |
| 부분 | 배포 설정(스텁·`py.typed` 없음, 매니페스트가 패키지 밖), `Modifier` 체인·오버로드·`Dp` 숫자 허용(바인더 계층 대상 테스트가 실패 중), Material 3 위젯(렌더 증거는 python-multiplatform 에만), `Icon`·색 스킴(import 만 됨), `Alignment`/`Arrangement` 상수(괄호 없이 읽는 표기로 확정, `pythonx.*` 재노출 전) |
| 계획 | `pythonx` 를 실제 디스크 패키지로 재구성, `.pyi` 동봉, `remember_saveable`·`DefaultIcons`·코루틴 스코프 |

### 테스트 기준선

```
python3 -m pytest tests -q
  PythonMultiplatform 체크아웃 없음       40 passed, 37 skipped
  PYTHONMULTIPLATFORM_HOME 지정            40 passed, 37 failed  (register_package 없음)
```

37 개 실패는 **예상된 것**이다. 테스트 하네스(`tests/adapter.py`)가 바인더에게
`register_package('pythonx.compose', 'androidx.compose')` 를 시키는데, 바인더는 더 이상 이름을
바꾸지 않는다. 이 패키지 쪽 런타임이 아직 연결되지 않았으므로 해당 항목은 "부분" 으로 기록한다.
통과하는 40 개 중 다수는 *부재*(옛 토큰·삭제된 파일이 없음)를 확인하는 것이라 기능 진척으로 세지
않는다.

## 4. 구조

```
pythonx/compose/          import 패키지 (현재 대부분 독스트링만 있는 모듈)
  runtime/                @Composable
  ui/                     modifier.py (빈 Modifier 등록 지점), alignment.py
  layout/                 arrangement.py
  material3/              icon.py, color_scheme.py (호출 불가 기록용), 빈 파일 28 개
  lite/                   2024 JPype 프로토타입 (은퇴, 바이너리 97 개 추적 중)
  native/                 서브모듈 → thisisthepy/swing-graalvm-demo
pythonx-map.toml          pythonx ↔ androidx 매핑 매니페스트
tests/                    pytest (unittest 스타일)
test/                     2023–2024 Kotlin Multiplatform 샘플 (pycomposeui) — 처리 미정
docs/INTENT.md  docs/SPEC.md  docs/locale/  docs/guide/
tools/check_guide.py      가이드 사이트 검사 (가이드의 테스트)
```

## 5. 빌드·테스트

```bash
python3 -m pytest tests -q                       # 파이썬 테스트
PYTHONMULTIPLATFORM_HOME=<checkout> python3 -m pytest tests -q   # 바인더 계층 포함
python3 tools/check_guide.py                     # 가이드: HTML 파싱, 링크, en/ko 짝
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

1. **`test/` 디렉터리** — 2023–2024 Kotlin Multiplatform 샘플. 유지 / 이동 / 삭제 중 무엇인지.
   결정 전까지 손대지 않는다.
2. **현재 코드·테스트가 반대 구조를 전제한다.** `runtime/__init__.py`, `ui/__init__.py`,
   `ui/modifier.py` 의 독스트링과 `test_runtime_module.py`·`test_ui_init_module.py` 의 4 개 테스트가
   "합성된 `pythonx`(`__path__ = []`) 때문에 디스크 파일을 import 할 수 없다" 를 전제·단언한다.
   사용자 지시(실제 패키지)와 충돌하므로 재작성 대상이다.
3. **`main.App` / `App.update`** — 노트북의 라이브 앱 객체를 이 패키지가 제공하는지.
4. **`Column`·`Row`·`Spacer` 의 import 위치** — 노트북은 `material3`, Kotlin 은 `foundation.layout`.
5. **노트북식 편의 표기** — 소문자 `modifier` 인스턴스, `DefaultIcons`, ARGB 정수 색,
   `Spacer(start=..., top=...)`.
6. **정렬 상수의 묶음 표기** — 노트북은 `Alignment.Horizontal.End`, Kotlin·바인더는 평평한
   `Alignment.End`. 재노출 때 묶음을 둘지 미정. (호출이냐 읽기냐는 확정: 괄호 없이 읽는다.)
7. **`pythonx/compose/lite/release/`** 의 Windows 바이너리·jar 97 개와 빈 `material3/*.py` 28 개,
   서브모듈 `native` 의 처리.
8. **`pythonx-map.toml` 의 이중 표기** — `pythonx.compose.layout` 과
   `pythonx.compose.foundation.layout` 를 둘 다 유지할지.
9. **릴리스·Pages 활성화** — `tools/release/` 와 `.github/workflows/`(release-sync, main-source-guard,
   pages)는 들어와 있다. 실제로 돌려면 원격 푸시, `RELEASE_PR_TOKEN` 시크릿, main 보호 적용이
   필요하고, 셋 다 메인테이너 승인 사항이다.

## 8. 관련 저장소

| 저장소 | 관계 |
|---|---|
| `python-multiplatform` | 바인더. 이 패키지가 런타임에 의존하는 대상. 이 저장소에서는 읽기 전용 |
| `toolchain` | Gradle 빌드 플러그인 |
| `pypackpack` | 파이썬 프로젝트 배포 |
| `torchnative`, `Gemstone` | 같은 생태계의 다른 프로젝트 |
