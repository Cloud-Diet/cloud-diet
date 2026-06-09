# Cloud Diet 사용법

이 문서는 Cloud Diet 프로그램을 처음 실행하는 사용자 기준으로 설치, 샘플 실행, 실제 AWS 실행, 알림 등록, 결과 확인 방법을 정리한 사용 설명서입니다.

## 1. 프로그램 개요

Cloud Diet은 AWS EC2, EBS, CloudWatch 데이터를 수집해 비용 낭비 후보를 찾는 Python 배치 프로그램입니다.

실행 흐름은 다음과 같습니다.

```text
설정 로드 -> 리소스 수집 -> 표준 JSON 변환 -> 룰 기반 분석 -> 권고문 생성 -> 리포트 저장 -> Discord/Slack 알림
```

중요한 점은 자동 삭제, 자동 중지, 자동 다운사이징을 하지 않는다는 것입니다. 프로그램은 운영자가 확인할 수 있는 후보와 권고문만 제공합니다.

## 2. 실행 전 준비

필요한 도구:

| 항목 | 용도 |
|---|---|
| Python 3.11 이상 | 로컬 실행 |
| Docker Desktop | 컨테이너 실행 |
| AWS Access Key 또는 AWS Profile | 실제 AWS 리소스 조회 |
| Discord Webhook 또는 Slack Webhook | 알림 발송 |
| OpenAI API Key | LLM 권고문 생성 |

샘플 데이터로만 실행할 때는 AWS Key, OpenAI API Key, Webhook이 없어도 됩니다.

## 3. 로컬 설치

프로젝트 폴더에서 아래 명령을 실행합니다.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` 파일은 실제 비밀값을 담는 파일입니다. GitHub에 올리면 안 됩니다.

## 4. 샘플 데이터로 실행하기

처음에는 실제 AWS를 연결하기 전에 샘플 모드로 실행하는 것이 좋습니다.

`.env`에서 아래 값으로 설정합니다.

```env
COLLECTOR_MODE=sample
NOTIFIER=console
LLM_ENABLED=false
```

실행 명령:

```powershell
python -m app.main
```

샘플 실행 화면:

![Cloud Diet sample run](images/sample-run-console.png)

샘플 실행에서는 `configs/sample_resources.json`에 들어 있는 EC2/EBS 예시 데이터를 분석합니다. 정상 실행되면 콘솔에 일일 비용 최적화 후보 리포트가 출력됩니다.

## 5. 결과 파일 확인

실행 결과는 `outputs/` 폴더에 저장됩니다.

![Cloud Diet outputs folder](images/outputs-files.png)

생성되는 파일:

| 파일 | 설명 |
|---|---|
| `resources_YYYYMMDD_HHMMSS.json` | 정규화된 EC2/EBS 리소스 목록 |
| `findings_YYYYMMDD_HHMMSS.json` | 룰 기반 분석 결과 |
| `report_YYYYMMDD_HHMMSS.md` | 운영자가 읽는 Markdown 리포트 |
| `cloud_diet.log` | 실행 로그 |

## 6. 실제 AWS 데이터로 실행하기

`.env`를 실제 실행용으로 바꿉니다.

```env
COLLECTOR_MODE=aws
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-northeast-2
NOTIFIER=console
LLM_ENABLED=false
```

먼저 `NOTIFIER=console`, `LLM_ENABLED=false`로 실행해 AWS 수집과 룰 분석이 정상인지 확인합니다.

```powershell
python -m app.main
```

정상 확인 후 OpenAI와 Webhook을 켭니다.

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
LLM_ENABLED=true
```

## 7. Discord 알림 설정

Discord에서 Webhook을 만드는 순서:

1. 알림을 받을 Discord 채널을 선택합니다.
2. 채널 설정에서 `연동` 또는 `Integrations` 메뉴를 엽니다.
3. `Webhook`을 새로 만듭니다.
4. 이름을 `Cloud Diet`으로 지정합니다.
5. Webhook URL을 복사합니다.
6. `.env`에 등록합니다.

```env
NOTIFIER=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

테스트할 때는 다음 조합을 권장합니다.

```env
COLLECTOR_MODE=sample
NOTIFIER=discord
LLM_ENABLED=false
```

이 상태로 `python -m app.main`을 실행하면 샘플 리포트가 Discord 채널로 전송됩니다.

## 8. Slack 알림 설정

Slack Incoming Webhook URL을 만든 뒤 `.env`에 등록합니다.

```env
NOTIFIER=slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Discord와 Slack 중 하나만 선택해서 사용합니다. 둘 다 보내려면 `app/notifiers/__init__.py`에 `both` 옵션을 추가하면 됩니다.

## 9. Docker로 실행하기

이미지 빌드:

```powershell
docker build -t cloud-diet:latest .
```

수동 실행:

```powershell
docker run --rm --env-file .env -v ${PWD}/outputs:/app/outputs -v ${PWD}/configs:/app/configs cloud-diet:latest
```

Docker Compose 실행:

```powershell
docker compose up --build
```

Cloud Diet은 배치 프로그램이므로 실행이 끝나면 컨테이너가 종료됩니다. 종료는 오류가 아니라 정상 동작입니다.

## 10. 주기 실행 등록

Linux cron 예시:

```cron
0 9 * * * cd /home/ubuntu/cloud-diet && docker compose run --rm cloud-diet >> /home/ubuntu/cloud-diet/outputs/cron.log 2>&1
```

Windows 작업 스케줄러 예시:

```text
프로그램: powershell.exe
인수: -NoProfile -ExecutionPolicy Bypass -Command "cd 'C:\path\to\cloud-diet'; docker compose run --rm cloud-diet"
```

## 11. Docker Stack / Portainer 등록

Swarm Stack 예시:

```powershell
docker build -t cloud-diet:latest .
docker stack deploy -c docker-stack.example.yml cloud-diet
```

Portainer 등록 순서:

1. Portainer에서 `Stacks`로 이동합니다.
2. `Add stack`을 선택합니다.
3. 이름을 `cloud-diet`로 입력합니다.
4. `Web editor`에 `docker-stack.example.yml` 내용을 넣습니다.
5. Environment variables에 `.env`의 실제 값을 등록합니다.
6. `Deploy the stack`을 누릅니다.

배치 작업은 Stack보다 cron이나 작업 스케줄러가 더 잘 맞습니다. Stack은 이미지와 환경을 관리하는 보조 수단으로 쓰고, 실제 주기 실행은 스케줄러에서 호출하는 방식을 권장합니다.

## 12. 자주 쓰는 설정

| 설정 | 예시 | 설명 |
|---|---|---|
| `COLLECTOR_MODE` | `sample`, `aws` | 샘플 데이터 또는 실제 AWS 조회 |
| `NOTIFIER` | `console`, `discord`, `slack`, `none` | 알림 채널 |
| `LLM_ENABLED` | `true`, `false` | LLM 권고문 생성 여부 |
| `ANALYSIS_DAYS` | `14` | CloudWatch 분석 기간 |
| `MAX_FINDINGS_PER_REPORT` | `20` | 알림에 포함할 최대 finding 수 |
| `RULE_CONFIG_PATH` | `configs/rules.yaml` | 룰 설정 파일 경로 |

## 13. 문제 해결

### 실행은 됐는데 Discord 알림이 오지 않음

- `NOTIFIER=discord`인지 확인합니다.
- `DISCORD_WEBHOOK_URL`이 비어 있지 않은지 확인합니다.
- Webhook이 연결된 Discord 채널이 삭제되지 않았는지 확인합니다.
- 먼저 `COLLECTOR_MODE=sample`, `LLM_ENABLED=false`로 테스트합니다.

### AWS 인증 오류가 발생함

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` 값을 확인합니다.
- 로컬 AWS Profile을 쓰는 경우 `AWS_PROFILE`이 실제 존재하는지 확인합니다.
- Docker 컨테이너에서는 호스트의 AWS Profile이 자동으로 들어가지 않습니다. 이 경우 환경변수 방식이 가장 단순합니다.

### OpenAI API 오류가 발생함

- `OPENAI_API_KEY`가 설정되어 있는지 확인합니다.
- `LLM_ENABLED=false`로 실행하면 LLM 없이 fallback 권고문을 생성합니다.
- LLM 호출이 실패해도 프로그램은 리포트 저장과 알림을 계속 수행하도록 설계되어 있습니다.

## 14. 안전 주의사항

- 이 프로그램은 비용 절감 후보를 알려줄 뿐 실제 리소스를 변경하지 않습니다.
- EBS 삭제, EC2 중지, 인스턴스 다운사이징은 반드시 사람이 최종 확인 후 수행해야 합니다.
- `.env` 파일과 Webhook URL은 외부에 공유하지 않습니다.
- AWS IAM 권한은 읽기 전용으로 제한하는 것이 좋습니다.
## 2026-06-09 리포트 해석 가이드

리포트는 우선순위별 섹션으로 나뉩니다.

| 섹션 | 의미 |
|---|---|
| 즉시 검토 대상 | 근거가 충분하고 비용 영향이 있어 빠른 검토가 필요합니다. |
| 검토 대상 | 비용 최적화 가능성이 있어 운영자 확인이 필요합니다. |
| 관찰 대상 | 근거가 일부 부족해 추가 관찰을 권장합니다. |
| 제외 권장 대상 | prod, critical 같은 보호 태그로 인해 조치 대상에서 제외하는 편이 안전합니다. |

`confidence_score`는 0~100 사이의 규칙 기반 점수입니다. 높을수록 비용 낭비 후보일 가능성이 크지만, 실제 조치는 소유자와 운영 맥락을 확인한 뒤 진행해야 합니다.

EBS finding의 `safe_action=snapshot_before_delete`는 삭제 전 스냅샷 검토를 뜻합니다. Cloud Diet가 스냅샷 생성이나 볼륨 삭제 API를 호출한다는 의미가 아닙니다.

EC2 finding의 `recommended_instance_type`은 다운사이즈 확정값이 아니라 검토 후보입니다. 피크 트래픽, 배치 작업, 예약 작업, 서비스 SLO를 확인한 뒤 변경 여부를 결정하세요.

