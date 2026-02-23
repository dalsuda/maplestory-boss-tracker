# 🗡️ 메이플스토리 주간 보스 수익 계산기

메이플스토리 다중 캐릭터의 주간 보스 클리어 수익을 추적하고, BI 대시보드로 시각화하는 데스크탑 앱입니다.

---

## 📌 프로젝트 개요

메이플스토리는 캐릭터마다 매주 초기화되는 보스 레이드를 통해 수익을 얻는 구조입니다.
계정당 최대 수십 개의 캐릭터를 운용하기 때문에, 어떤 캐릭터가 어떤 보스를 클리어했는지 
수동으로 추적하는 것이 번거로웠습니다.

이 앱은 그 문제를 해결하면서, 동시에 아래 기술들을 실제로 적용해보는 포트폴리오 프로젝트입니다.

- **Nexon Open API** 연동으로 캐릭터 정보 자동 수집
- **SQLite + Parquet 이중 저장소** 설계
- **Polars** 기반 통계 집계
- **PySide6** BI 대시보드 UI

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| Language | Python 3.11+ |
| UI | PySide6 (Qt6) |
| DB | SQLite |
| 통계 처리 | Polars, Parquet |
| 외부 API | Nexon Open API |

---

## 🏗️ 아키텍처

### 디렉토리 구조

```
├── main.py                        # 진입점
├── config.py                      # 상수·경로·API 키
│
├── api/
│   └── nexon_api.py               # Nexon API 호출, 이미지 캐싱, 비동기 스레드
│
├── data_layer/
│   ├── database.py                # SQLite 연결·테이블 초기화
│   ├── data_manager.py            # CRUD, 주차 계산, 시세 이력 관리
│   └── parquet_store.py           # SQLite → Parquet 스냅샷, Polars 집계
│
├── ui/
│   ├── app.py                     # 최상위 위젯, 탭 조립, 트레이
│   ├── checklist_tab.py           # 체크리스트 탭
│   ├── stats_tab.py               # BI 대시보드 탭 3개
│   ├── styles.py                  # QSS 스타일 상수
│   └── widgets/
│       └── character_sidebar.py   # 아이콘 기반 캐릭터 사이드바
│
└── utils/
    └── formatters.py              # 한글 단위 포맷 (억·만·메소)
```

### 데이터 흐름

```
사용자 입력
    │
    ├─ 캐릭터 추가 ──→ Nexon API ──→ SQLite (characters)
    │
    ├─ 보스 체크 ────→ SQLite (weekly_checks)  ← 실시간 쓰기
    │
    └─ 보스 시세 변경 → SQLite (boss_list, boss_price_history)
                        │
                        │  통계 탭 진입 시 snapshot()
                        ▼
                  Parquet 스냅샷
                        │
                        │  read_parquet() + Polars 집계
                        ▼
                  BI 대시보드 차트
```

---

## 💡 주요 설계 결정

### 1. SQLite + Parquet 이중 저장소

| 저장소 | 역할 | 이유 |
|---|---|---|
| SQLite | 실시간 쓰기, 원본 데이터 | 트랜잭션 보장, 즉각적인 체크 상태 반영 |
| Parquet | 통계 전용 읽기 | Polars와의 궁합, 컬럼 기반 집계 성능 |

통계가 필요할 때만 `snapshot()`으로 SQLite → Parquet 동기화하고,
이후 집계는 전부 Polars로 처리합니다.

### 2. 보스 시세 이력 보호

보스 클리어 수익은 게임 패치로 비주기적으로 조정됩니다.
시세를 단순히 덮어쓰면 과거 수익 내역이 왜곡되는 문제가 생깁니다.

```
weekly_checks.boss_value  ← 체크 당시 시세를 스냅샷으로 저장
boss_price_history        ← 변경 이력 기록 (언제, 얼마로, 메모)

시세 업데이트 시:
  UPDATE weekly_checks SET boss_value = ?
  WHERE boss_name = ? AND week_key >= ?  ← applied_from 이후만 갱신
```

과거 주차의 `boss_value`는 절대 변경하지 않아, 수익 내역의 정합성을 보장합니다.

### 3. 주차 기준: 목요일

메이플스토리의 주간 보스는 목요일 자정에 초기화됩니다.
ISO 기준 월요일 시작과 달리, 목요일을 기준으로 주차 키를 계산합니다.

```python
def current_week_key() -> str:
    today = date.today()
    offset = (today.weekday() - 3) % 7  # 목요일(3) 기준
    thursday = today - timedelta(days=offset)
    year, week, _ = thursday.isocalendar()
    return f"{year}-{week}"
```

---

## 📊 BI 대시보드

통계 탭 3개로 구성되어 있으며 모두 Polars로 집계합니다.

| 탭 | 차트 | 집계 방식 |
|---|---|---|
| 📊 누적 수익 | 주차별 수익 막대 그래프 | `group_by("week_key").agg(sum)` |
| 🥧 보스별 기여도 | 주간·누적 도넛 파이 차트 | `group_by("boss_name").agg(sum)` |
| 📈 캐릭터별 통계 | 수익 꺾은선 + 달성률 막대 | `filter + group_by("character")` |

Parquet 내보내기 기능으로 외부 분석 도구(Jupyter, DBeaver 등)에서도 활용 가능합니다.

---

## 🚀 실행 방법

### 1. 의존성 설치

```bash
pip install PySide6 polars requests
```

### 2. 기존 데이터 마이그레이션 (JSON → SQLite)

기존 `boss_data.json`이 있는 경우:

```bash
python migrate.py
```

### 3. 실행

```bash
python main.py
```

---

## 📦 데이터 스키마

```sql
-- 캐릭터 정보
characters (name PK, ocid, level, job, power, image_url)

-- 전역 보스 목록 (현재 시세)
boss_list (name PK, value)

-- 보스 시세 변경 이력
boss_price_history (id PK, boss_name, value, applied_from, note)

-- 주차별 체크 상태 ★ 핵심
weekly_checks (week_key, character, boss_name, boss_value, checked)
              └─ boss_value: 체크 당시 시세 스냅샷 (과거 내역 보호)
```

---

## 📝 개발 과정에서 배운 점

**데이터 정합성의 중요성**
처음에는 JSON 단일 파일로 관리했습니다. 시세가 변경될 때 과거 데이터가 같이 바뀌는 문제를 겪으면서, 원본 데이터 보호를 위한 스냅샷 설계의 필요성을 직접 체감했습니다.

**읽기와 쓰기 저장소 분리**
실시간 쓰기(SQLite)와 통계 읽기(Parquet+Polars)를 분리하면서, OLTP와 OLAP의 특성 차이를 실제 코드로 구현해볼 수 있었습니다.

**리팩토링의 효과**
초기 700줄짜리 단일 클래스(`BossTrackerApp`)를 레이어별로 분리하면서, 각 클래스가 단일 책임을 갖도록 구조를 개선했습니다. 이후 기능 추가 시 수정 범위가 명확해지는 효과를 경험했습니다.
