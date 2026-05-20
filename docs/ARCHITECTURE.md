# Cloud Diet 아키텍처 문서

이 문서는 프로젝트 내부 파일이 어떤 기능을 담당하는지, 프로그램이 어떤 순서로 실행되는지, 모듈 사이에서 데이터가 어떻게 전달되는지 설명합니다.

## 전체 실행 흐름

```text
python -m app.main
  |
  +-- app.config.load_settings()
  |     .env, configs/rules.yaml 읽기
  |
  +-- Collector
  |     AWS EC2 / EBS / CloudWatch API 호출
  |
  +-- Normalizer
  |     AWS 원본 응답을 표준 JSON 리소스 모델로 변환
  |
  +-- Rule Analyzer
  |     CPU, EBS 연결 상태 기준으로 findings 생성
  |
  +-- LLM Recommender
  |     findings를 운영자용 한국어 권고문으로 변환
  |
  +-- Reporter
  |     outputs/*.json, outputs/*.md 저장
  |
  +-- Notifier
        Discord 또는 Slack Webhook으로 일일 요약 발송
```

`COLLECTOR_MODE=sample`이면 AWS API를 호출하지 않고 `configs/sample_resources.json`을 바로 읽습니다. 발표, 데모, 로컬 테스트에 유용합니다.

## 파일별 역할

| 파일 | 기능 | 입력 | 출력 |
|---|---|---|---|
| `app/main.py` | 전체 배치 흐름 제어 | 환경 설정, AWS 또는 샘플 데이터 | 리포트 파일, 알림 메시지 |
| `app/config.py` | `.env`, `rules.yaml` 로딩 | 환경변수, YAML | `Settings` 객체 |
| `app/collectors/aws_ec2_collector.py` | EC2 인스턴스 원본 데이터 수집 | AWS 인증, 리전 | EC2 raw dict list |
| `app/collectors/aws_ebs_collector.py` | EBS 볼륨 원본 데이터 수집 | AWS 인증, 리전 | EBS raw dict list |
| `app/collectors/cloudwatch_collector.py` | EC2 CPU 평균/최대 메트릭 수집 | 표준 EC2 리소스, 기간 | CPU 메트릭이 붙은 리소스 |
| `app/normalizers/resource_normalizer.py` | AWS raw 응답 정규화 | EC2/EBS raw dict list | 표준 리소스 JSON list |
| `app/analyzers/rule_analyzer.py` | 비용 낭비 후보 탐지 | 표준 리소스 JSON, rules | finding JSON list |
| `app/recommenders/llm_recommender.py` | 권고문 생성 | finding JSON | 한국어 권고문 list |
| `app/notifiers/discord_notifier.py` | Discord 발송 | 메시지 문자열, Webhook URL | Discord 채널 메시지 |
| `app/notifiers/slack_notifier.py` | Slack 발송 | 메시지 문자열, Webhook URL | Slack 채널 메시지 |
| `app/reporters/markdown_reporter.py` | 결과 저장과 요약 생성 | 리소스, findings, 권고문 | JSON/Markdown 파일, 요약 문자열 |
| `app/utils/logger.py` | 로그 설정 | 로그 레벨, 출력 폴더 | 콘솔 로그, `cloud_diet.log` |

## 모듈 책임 분리

### Collector

Collector는 원본 데이터를 가져오는 일만 합니다. EC2 Collector는 `describe_instances`, EBS Collector는 `describe_volumes`, CloudWatch Collector는 `get_metric_statistics`를 호출합니다. 이 단계에서는 비용 낭비 여부를 판단하지 않습니다.

### Normalizer

Normalizer는 AWS 응답 구조를 프로젝트 내부 표준 모델로 바꿉니다. 예를 들어 EC2의 `InstanceId`, `InstanceType`, `State.Name`, `Tags`를 `resource_id`, `instance_type`, `state`, `tags`로 정리합니다.

### Analyzer

Analyzer는 LLM을 쓰지 않고 deterministic rule만 사용합니다. 현재 룰은 다음과 같습니다.

| 룰 | 조건 | Finding type | 심각도 |
|---|---|---|---|
| R-EC2-001 | 최근 N일 CPU 평균 < `cpu_avg_threshold` | `possible_overprovisioned_ec2` | medium |
| R-EC2-002 | 최근 N일 CPU 최대 < `cpu_max_threshold` | `low_peak_usage_ec2` | low |
| R-EBS-001 | `state=available` and `detached_days >= detached_days_threshold` | `unused_ebs_volume` | high |

### Recommender

Recommender는 Analyzer가 만든 finding을 자연어로 설명합니다. `OPENAI_API_KEY`가 있고 `LLM_ENABLED=true`이면 OpenAI API를 호출합니다. 키가 없거나 API 호출이 실패하면 fallback 권고문을 생성합니다.

중요한 제한:

- LLM은 삭제, 축소, 중지를 확정적으로 말하지 않습니다.
- LLM 입력에는 AWS raw 전체 응답을 넣지 않습니다.
- 비용 절감액을 임의로 만들지 않습니다.

### Reporter

Reporter는 실행 결과를 `outputs/`에 저장합니다. 리소스 원본 추적을 위해 `resources_*.json`, 탐지 결과 확인을 위해 `findings_*.json`, 사람이 읽는 보고서를 위해 `report_*.md`를 저장합니다.

### Notifier

Notifier는 `NOTIFIER` 값에 따라 발송 대상을 결정합니다.

| 값 | 동작 |
|---|---|
| `discord` | Discord Webhook으로 발송 |
| `slack` | Slack Incoming Webhook으로 발송 |
| `console` | 콘솔에 출력 |
| `none` | 발송하지 않음 |

## 데이터 전달 방식

모듈 사이 데이터는 Python `dict`와 `list[dict]`로 전달됩니다. 네트워크 전송은 AWS API 호출과 Webhook POST 두 지점에서만 발생합니다.

1. AWS API 응답: AWS SDK가 Python dict로 반환합니다.
2. 내부 표준 모델: Normalizer가 list[dict]로 변환합니다.
3. Finding 모델: Analyzer가 list[dict]로 생성합니다.
4. LLM 입력: Finding에서 필요한 필드만 JSON 문자열로 전달합니다.
5. 알림: Reporter가 만든 요약 문자열을 Webhook JSON body로 POST합니다.

Discord 전송 예:

```json
{
  "content": "[Cloud Diet] 일일 비용 최적화 후보 리포트..."
}
```

Slack 전송 예:

```json
{
  "text": "[Cloud Diet] 일일 비용 최적화 후보 리포트..."
}
```

## 설정 구조

`app/config.py`는 다음 순서로 설정을 만듭니다.

1. `.env` 로드
2. `configs/rules.yaml` 로드
3. 환경변수로 일부 값을 덮어쓰기
4. `Settings` dataclass 생성

환경변수가 우선입니다. 예를 들어 `rules.yaml`에 `analysis_days: 14`가 있어도 `.env`에 `ANALYSIS_DAYS=7`이 있으면 7일 기준으로 분석합니다.

