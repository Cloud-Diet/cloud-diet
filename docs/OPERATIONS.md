# Cloud Diet 운영 가이드

이 문서는 로컬 실행, Docker 실행, Discord/Slack 등록, cron 등록, Docker Stack/Portainer 등록 방법을 설명합니다.

## 1. 로컬 개발 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

샘플 실행용 `.env`:

```env
COLLECTOR_MODE=sample
NOTIFIER=console
LLM_ENABLED=false
OUTPUT_DIR=outputs
RULE_CONFIG_PATH=configs/rules.yaml
```

실행:

```bash
python -m app.main
```

테스트:

```bash
pytest
```

## 2. AWS 권한

MVP는 읽기 전용 권한만 필요합니다. 최소 권한 예시는 다음과 같습니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

이 프로젝트는 리소스를 삭제하거나 변경하지 않으므로 `ec2:TerminateInstances`, `ec2:StopInstances`, `ec2:DeleteVolume`, `ec2:ModifyInstanceAttribute` 같은 권한을 주지 않아도 됩니다.

## 3. Discord 등록

Discord Webhook 등록 순서:

1. Discord 서버에서 알림을 받을 채널을 선택합니다.
2. 채널 설정에서 `Integrations` 또는 `연동` 메뉴로 들어갑니다.
3. `Webhooks`에서 새 Webhook을 만듭니다.
4. 이름을 `Cloud Diet`로 지정합니다.
5. Webhook URL을 복사합니다.
6. `.env`에 붙여넣습니다.

```env
NOTIFIER=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

처음에는 아래처럼 샘플 데이터와 fallback 권고문으로 테스트하면 안전합니다.

```env
COLLECTOR_MODE=sample
LLM_ENABLED=false
NOTIFIER=discord
```

## 4. Slack 등록

Slack Incoming Webhook을 만든 뒤 `.env`에 등록합니다.

```env
NOTIFIER=slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Slack과 Discord 중 하나만 선택해서 쓰면 됩니다. 둘 다 보내고 싶다면 `app/notifiers/__init__.py`의 dispatch를 확장해 `both` 옵션을 추가하면 됩니다.

## 5. Docker 실행

빌드:

```bash
docker build -t cloud-diet:latest .
```

Windows PowerShell 수동 실행:

```powershell
docker run --rm --env-file .env -v ${PWD}/outputs:/app/outputs -v ${PWD}/configs:/app/configs cloud-diet:latest
```

Linux/macOS 수동 실행:

```bash
docker run --rm --env-file .env -v $(pwd)/outputs:/app/outputs -v $(pwd)/configs:/app/configs cloud-diet:latest
```

Compose 실행:

```bash
docker compose up --build
```

배치 앱이므로 실행이 끝나면 컨테이너가 종료됩니다. 이것이 정상 동작입니다.

## 6. cron 등록

Linux 서버에서 매일 오전 9시에 실행:

```cron
0 9 * * * cd /home/ubuntu/cloud-diet && docker run --rm --env-file .env -v $(pwd)/outputs:/app/outputs -v $(pwd)/configs:/app/configs cloud-diet:latest >> /home/ubuntu/cloud-diet/outputs/cron.log 2>&1
```

Compose 기반으로 실행:

```cron
0 9 * * * cd /home/ubuntu/cloud-diet && docker compose run --rm cloud-diet >> /home/ubuntu/cloud-diet/outputs/cron.log 2>&1
```

## 7. Windows 작업 스케줄러 등록

Windows에서는 작업 스케줄러에 PowerShell 명령을 등록합니다.

프로그램:

```text
powershell.exe
```

인수:

```text
-NoProfile -ExecutionPolicy Bypass -Command "cd 'C:\path\to\cloud-diet'; docker compose run --rm cloud-diet"
```

## 8. Docker Stack 등록

Docker Swarm을 사용하는 경우:

```bash
docker build -t cloud-diet:latest .
docker stack deploy -c docker-stack.example.yml cloud-diet
```

다만 현재 앱은 배치 컨테이너를 1회 실행하는 구조입니다. Swarm Stack은 장기 실행 서비스에 더 잘 맞습니다. Cloud Diet처럼 하루 1회 실행되는 작업은 cron에서 `docker run`을 호출하는 방식이 더 단순합니다.

Stack으로 꼭 관리하려면 다음 전략 중 하나를 선택합니다.

| 방식 | 설명 |
|---|---|
| Stack + 수동 실행 | Stack에는 이미지/환경만 관리하고 실제 실행은 cron이 담당 |
| Stack + 외부 스케줄러 | Jenkins, GitHub Actions, 서버 cron이 `docker service update --force` 또는 `docker run` 호출 |
| Kubernetes CronJob | 운영 환경이 Kubernetes면 CronJob 리소스로 스케줄링 |

## 9. Portainer Stack 등록

Portainer에서 등록:

1. `Stacks`로 이동합니다.
2. `Add stack`을 누릅니다.
3. 이름을 `cloud-diet`로 입력합니다.
4. `Web editor`에 `docker-stack.example.yml` 내용을 넣습니다.
5. `Environment variables`에 `.env` 값을 입력합니다.
6. `Deploy the stack`을 누릅니다.

Portainer에서 `.env` 파일을 직접 관리하기 어렵다면 `docker-compose.yml`의 `environment:` 블록을 사용해 등록할 수 있습니다. 단, Webhook URL이나 API Key가 화면에 노출될 수 있으므로 Portainer의 secret 관리 방식 또는 서버의 `.env` 파일을 사용하는 편이 안전합니다.

## 10. 운영 점검 체크리스트

배포 전:

- `.env`가 Git에 커밋되지 않았는지 확인
- `NOTIFIER=console`로 샘플 실행 성공 확인
- Discord 또는 Slack 테스트 메시지 확인
- AWS IAM 권한이 읽기 전용인지 확인
- `outputs/` 볼륨이 호스트에 마운트되는지 확인

운영 중:

- `outputs/cloud_diet.log` 확인
- `outputs/findings_*.json`에서 룰 탐지 결과 확인
- 리포트가 매일 생성되는지 확인
- 메시지 폭주 시 `MAX_FINDINGS_PER_REPORT` 낮추기
- 룰이 너무 민감하면 `configs/rules.yaml` 임계값 조정

## 11. 문제 해결

### Discord 메시지가 오지 않음

- `NOTIFIER=discord`인지 확인합니다.
- `DISCORD_WEBHOOK_URL`이 비어 있지 않은지 확인합니다.
- Webhook이 연결된 채널이 삭제되지 않았는지 확인합니다.
- 샘플 모드로 먼저 테스트합니다.

### AWS 인증 오류

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`을 확인합니다.
- 로컬 Profile 사용 시 `AWS_PROFILE`이 실제 존재하는지 확인합니다.
- 컨테이너에서 실행하면 호스트의 AWS profile 파일이 자동으로 들어가지 않습니다. 이 경우 Access Key 환경변수 또는 별도 볼륨 마운트가 필요합니다.

### LLM 권고문이 생성되지 않음

- `LLM_ENABLED=true`인지 확인합니다.
- `OPENAI_API_KEY`가 설정되어 있는지 확인합니다.
- API 호출 실패 시 프로그램은 자동으로 fallback 권고문을 사용합니다.
