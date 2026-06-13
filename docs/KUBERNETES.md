mkdir -p docs

cat > docs/KUBERNETES.md <<'EOF'
# Cloud Diet Kubernetes 실행 가이드

Cloud Diet를 Kubernetes CronJob으로 실행하는 방법을 설명합니다.

## 검증된 실행 흐름

```text
Kubernetes CronJob
  → Cloud Diet 컨테이너 실행
  → 샘플 데이터 분석
  → 규칙 기반 비용 최적화 후보 탐지
  → OpenAI API 한국어 권고문 생성
  → Discord Webhook 전송
  → Job 종료
```

샘플 데이터 기반 통합 테스트에서 Kubernetes Job 완료와 Discord 메시지 수신을 확인했습니다.

## 사전 요구사항

- Docker
- kubectl
- kind
- Discord Incoming Webhook URL
- OpenAI API Key
- Cloud Diet 저장소

설치 상태를 확인합니다.

```bash
docker --version
kubectl version --client
kind version
docker info
```

## 로컬 Kubernetes 클러스터 생성

```bash
kind create cluster --name cloud-diet --wait 120s
kubectl config use-context kind-cloud-diet
kubectl cluster-info --context kind-cloud-diet
kubectl get nodes
```

노드 상태가 `Ready`인지 확인합니다.

## 컨테이너 이미지 생성

```bash
docker build -t cloud-diet:0.1.0 .
kind load docker-image cloud-diet:0.1.0 --name cloud-diet
```

`k8s/cronjob.yaml`의 이미지 이름과 태그가 같아야 합니다.

```yaml
image: cloud-diet:0.1.0
imagePullPolicy: IfNotPresent
```

## Namespace 생성

```bash
kubectl apply -f k8s/namespace.yaml
kubectl get namespace cloud-diet
```

## Secret 생성

실제 OpenAI API Key와 Discord Webhook URL은 YAML이나 Git에 저장하지 않습니다.

```bash
read -s -p "Discord Webhook URL: " DISCORD_WEBHOOK_URL
echo

read -s -p "OpenAI API Key: " OPENAI_API_KEY
echo
```

Secret을 생성합니다.

```bash
kubectl create secret generic cloud-diet-secrets \
  --namespace cloud-diet \
  --from-literal=DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
```

입력값을 셸에서 제거합니다.

```bash
unset DISCORD_WEBHOOK_URL
unset OPENAI_API_KEY
```

Secret 존재 여부만 확인합니다.

```bash
kubectl get secret cloud-diet-secrets -n cloud-diet
```

Secret의 실제 내용은 터미널이나 발표 화면에 출력하지 마세요.

기존 Secret을 갱신할 때는 다음 명령을 사용합니다.

```bash
read -s -p "Discord Webhook URL: " DISCORD_WEBHOOK_URL
echo

read -s -p "OpenAI API Key: " OPENAI_API_KEY
echo

kubectl create secret generic cloud-diet-secrets \
  --namespace cloud-diet \
  --from-literal=DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client \
  -o yaml |
kubectl apply -f -

unset DISCORD_WEBHOOK_URL
unset OPENAI_API_KEY
```

## CronJob 배포

```bash
kubectl apply -f k8s/cronjob.yaml
kubectl get cronjob -n cloud-diet
kubectl describe cronjob cloud-diet -n cloud-diet
```

기본 스케줄은 매일 오전 9시입니다.

```yaml
schedule: "0 9 * * *"
timeZone: "Asia/Seoul"
```

## 수동 통합 테스트

예약 시간을 기다리지 않고 일회성 Job을 생성합니다.

```bash
JOB_NAME="cloud-diet-manual-$(date +%s)"

kubectl create job \
  --from=cronjob/cloud-diet \
  "$JOB_NAME" \
  -n cloud-diet
```

완료될 때까지 기다립니다.

```bash
kubectl wait \
  --for=condition=complete \
  "job/$JOB_NAME" \
  -n cloud-diet \
  --timeout=180s
```

상태와 로그를 확인합니다.

```bash
kubectl get jobs,pods -n cloud-diet
kubectl logs "job/$JOB_NAME" -n cloud-diet
```

정상 실행 시 다음 로그가 나타납니다.

```text
Cloud Diet batch started
Report files written
Cloud Diet batch finished
```

Discord 채널에 메시지가 도착했는지도 확인합니다.

## OpenAI API 사용 확인

Discord 메시지가 도착한 것만으로 OpenAI API 성공을 확정할 수는 없습니다. API 호출에 실패하면 fallback 권고문이 사용됩니다.

```bash
kubectl logs "job/$JOB_NAME" -n cloud-diet |
grep -Ei "LLM recommendation failed|using fallback|error|exception"
```

오류가 없다면 출력이 없어야 합니다.

OpenAI 사용량 대시보드에서도 요청 기록을 확인합니다.

테스트 비용을 줄이려면 `k8s/cronjob.yaml`에서 다음 값을 사용합니다.

```yaml
- name: MAX_FINDINGS_PER_REPORT
  value: "1"
```

Cloud Diet는 finding마다 OpenAI API를 한 번 호출합니다.

## AI 없이 실행

OpenAI API를 사용하지 않으려면 다음처럼 설정합니다.

```yaml
- name: LLM_ENABLED
  value: "false"
```

이 경우 규칙 기반 fallback 권고문이 Discord로 전송됩니다.

## 코드 변경 후 재배포

새 이미지 태그를 사용합니다.

```bash
docker build -t cloud-diet:0.1.1 .
kind load docker-image cloud-diet:0.1.1 --name cloud-diet
```

`k8s/cronjob.yaml`도 수정합니다.

```yaml
image: cloud-diet:0.1.1
```

변경사항을 적용합니다.

```bash
kubectl apply -f k8s/cronjob.yaml
```

이미 실행된 Job에는 변경사항이 적용되지 않으므로 새 Job을 생성합니다.

## 문제 해결

### Docker 접근 권한 오류

```text
permission denied while trying to connect to the docker API
```

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker info
```

### ImagePullBackOff

```bash
kind load docker-image cloud-diet:0.1.0 --name cloud-diet
kubectl describe pod -n cloud-diet
```

이미지 이름과 태그도 확인합니다.

### CreateContainerConfigError

```bash
kubectl get secret cloud-diet-secrets -n cloud-diet
kubectl describe pod -n cloud-diet
```

필요한 Secret 키:

```text
DISCORD_WEBHOOK_URL
OPENAI_API_KEY
```

### Job 실패

```bash
kubectl get jobs,pods -n cloud-diet
kubectl describe job "$JOB_NAME" -n cloud-diet
kubectl logs "job/$JOB_NAME" -n cloud-diet
```

### OpenAI 401

API 키가 잘못됐거나 폐기된 상태입니다. Secret을 새 키로 갱신합니다.

### OpenAI 429

크레딧 또는 사용 한도를 확인합니다. 테스트에는 `MAX_FINDINGS_PER_REPORT=1`을 권장합니다.

### Discord 404

Webhook URL이 잘못됐거나 삭제됐습니다. 새 Webhook을 만든 뒤 Secret을 갱신합니다.

## 리소스 삭제

수동 Job 삭제:

```bash
kubectl delete job "$JOB_NAME" -n cloud-diet
```

Cloud Diet 리소스 전체 삭제:

```bash
kubectl delete namespace cloud-diet
```

kind 클러스터 삭제:

```bash
kind delete cluster --name cloud-diet
```

## 보안 원칙

다음 파일과 값은 Git에 커밋하지 않습니다.

- `.env`
- 실제 Kubernetes Secret YAML
- OpenAI API Key
- Discord Webhook URL
- 민감 정보가 포함된 실행 로그

Git에는 다음 파일만 포함합니다.

```text
k8s/namespace.yaml
k8s/cronjob.yaml
k8s/secret.example.yaml
docs/KUBERNETES.md
```

커밋 전에 확인합니다.

```bash
git status
git diff --cached
```

실제 키가 노출됐다면 OpenAI 키와 Discord Webhook을 즉시 폐기하고 새로 발급해야 합니다.
EOF
