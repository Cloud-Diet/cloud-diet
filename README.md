# Cloud Diet

Cloud Diet는 AWS EC2, EBS, CloudWatch 데이터를 수집해 비용 낭비 후보를 찾고, 운영자가 검토하기 쉬운 한국어 리포트와 Slack/Discord/Console 알림을 생성하는 Docker 기반 Python 배치 애플리케이션입니다.

이 프로젝트의 목표는 자동 삭제나 자동 다운사이즈가 아닙니다. 모든 결과는 안전한 검토 후보이며, 실제 AWS 리소스를 변경하는 API는 호출하지 않습니다.

## 핵심 기능

| 기능 | 설명 |
|---|---|
| EC2 저사용 탐지 | 평균 CPU와 최대 CPU를 규칙 기반으로 분석해 다운사이즈 검토 후보를 찾습니다. |
| EBS 미사용 탐지 | 일정 기간 미연결 상태인 EBS 볼륨을 삭제 검토 후보로 찾습니다. |
| 신뢰도 점수 | 각 finding에 `confidence_score` 0~100 점수를 deterministic 방식으로 계산합니다. |
| 액션 우선순위 | `immediate_review`, `review`, `observe`, `excluded` 중 하나로 검토 우선순위를 분류합니다. |
| 안전 조치 안내 | EBS 삭제 후보는 `snapshot_before_delete`와 단계별 확인 절차를 함께 제공합니다. |
| 태그 메타데이터 | Owner, Team, Project, Environment, Service, Name 태그에서 담당/프로젝트/환경/서비스 정보를 추출합니다. |
| 비용 추정 | `configs/rules.yaml`의 로컬 가격표로 예상 월 비용과 절감액을 계산합니다. 가격이 없으면 `null`로 남깁니다. |
| EC2 타입 제안 | `t3.large -> t3.medium -> t3.small -> t3.micro` 범위에서만 안전한 검토 후보 타입을 제안합니다. |
| 리포트/알림 | JSON finding, Markdown 리포트, Console/Slack/Discord 요약에 핵심 판단 정보를 표시합니다. |
| 샘플 모드 | AWS 자격 증명 없이 `configs/sample_resources.json`만으로 주요 기능을 확인할 수 있습니다. |

## 실행 방법

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

샘플 모드 실행:

```env
COLLECTOR_MODE=sample
NOTIFIER=console
LLM_ENABLED=false
OUTPUT_DIR=outputs
RULE_CONFIG_PATH=configs/rules.yaml
```

```powershell
python -m app.main
```

실행 후 `outputs/`에 다음 파일이 생성됩니다.

| 파일 | 설명 |
|---|---|
| `resources_YYYYMMDD_HHMMSS.json` | 수집/정규화된 리소스 목록 |
| `findings_YYYYMMDD_HHMMSS.json` | 규칙 기반 분석 결과와 확장 필드 |
| `report_YYYYMMDD_HHMMSS.md` | 운영자 검토용 Markdown 리포트 |
| `cloud_diet.log` | 실행 로그 |

## 주요 출력 필드

finding에는 기존 `type`을 유지하면서 다음 필드가 추가됩니다.

```json
{
  "finding_type": "unused_ebs_volume",
  "confidence_score": 91,
  "action_priority": "immediate_review",
  "owner": "backend-team",
  "project": "capstone",
  "environment": "dev",
  "service": "api",
  "safe_action": "snapshot_before_delete",
  "estimated_monthly_savings": 8.0,
  "currency": "USD"
}
```

## 문서

- [전체 기능 설명서](docs/FEATURE_GUIDE.md)
- [변경 로그](CHANGELOG.md)
- [내부 파일 변경 내역](docs/INTERNAL_CHANGES.md)
- [아키텍처](docs/ARCHITECTURE.md)
- [데이터 형식](docs/DATA_FORMATS.md)
- [사용자 가이드](docs/USER_GUIDE.md)
- [운영 가이드](docs/OPERATIONS.md)

## 테스트

```powershell
pytest
```

현재 테스트는 분석기, 정규화, 설정, Markdown 리포터, 가격 추정 모듈을 검증합니다.
