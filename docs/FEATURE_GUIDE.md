# Cloud Diet 기능 설명서

## 1. 수집과 정규화

Cloud Diet는 AWS 모드에서 EC2, EBS, CloudWatch 데이터를 수집하고, 샘플 모드에서는 `configs/sample_resources.json`을 읽습니다. 정규화된 resource는 공통 필드인 `resource_type`, `resource_id`, `region`, `tags`를 갖습니다.

태그 메타데이터는 다음 키를 허용합니다.

| 출력 필드 | 입력 태그 후보 |
|---|---|
| `owner` | Owner, owner, Team, team |
| `project` | Project, project |
| `environment` | Environment, environment, Env, env |
| `service` | Service, service, Name |

태그가 없으면 `unknown`으로 처리합니다.

## 2. 규칙 기반 finding

분석기는 LLM이 아니라 deterministic rule로 finding을 만듭니다.

EC2 finding:

- `possible_overprovisioned_ec2`: 평균 CPU가 임계값보다 낮은 running EC2입니다.
- `low_peak_usage_ec2`: 최대 CPU가 임계값보다 낮은 running EC2입니다.

EBS finding:

- `unused_ebs_volume`: `available` 상태이며 `detached_days`가 임계값 이상인 EBS 볼륨입니다.

## 3. 신뢰도 점수

각 finding에는 `confidence_score`가 추가됩니다.

- 범위: 0~100
- 계산 주체: `app/analyzers/rule_analyzer.py`
- LLM은 점수를 생성하거나 수정하지 않습니다.

반영 요소:

- EC2 평균 CPU와 최대 CPU가 낮을수록 점수 상승
- 분석 기간이 충분하면 점수 상승
- 최근 생성 EC2면 점수 하락
- prod, production, critical 태그가 있으면 점수 하락
- EBS detached days가 길수록 점수 상승
- EBS state가 `available`이면 점수 상승

## 4. 액션 우선순위

각 finding에는 `action_priority`가 추가됩니다.

| 값 | 의미 |
|---|---|
| `immediate_review` | 근거가 충분하고 비용 영향이 있어 빠른 검토가 필요합니다. |
| `review` | 비용 최적화 가능성이 있어 운영자 확인이 필요합니다. |
| `observe` | 근거가 일부 부족해 관찰을 권장합니다. |
| `excluded` | prod/critical 등 보호 태그로 인해 조치 대상 제외를 권장합니다. |

## 5. EBS 안전 삭제 검토

EBS 미사용 finding은 바로 삭제를 지시하지 않습니다.

추가 필드:

```json
{
  "safe_action": "snapshot_before_delete",
  "recommended_steps": [
    "미연결 상태와 소유자를 확인합니다.",
    "삭제 전 스냅샷을 생성합니다.",
    "검토 기간 동안 스냅샷을 보관합니다.",
    "소유자 승인 후 볼륨 삭제 여부를 결정합니다."
  ]
}
```

실제 `create_snapshot` 또는 `delete_volume` API는 호출하지 않습니다.

## 6. 비용 추정

가격 추정은 `configs/rules.yaml`의 `pricing` 섹션을 사용합니다.

```yaml
pricing:
  currency: USD
  monthly_hours: 730
  ec2_hourly_prices:
    t3.micro: 0.0104
    t3.small: 0.0208
    t3.medium: 0.0416
    t3.large: 0.0832
  ebs_gb_month_prices:
    gp2: 0.10
    gp3: 0.08
```

출력 필드:

- `estimated_current_monthly_cost`
- `estimated_recommended_monthly_cost`
- `estimated_monthly_savings`
- `currency`
- `pricing_source`

가격 정보가 없으면 비용 필드는 `null`이며, 리포트에는 계산 불가로 표시됩니다.

## 7. EC2 권장 타입 제안

지원 범위:

```text
t3.large -> t3.medium
t3.medium -> t3.small
t3.small -> t3.micro
```

지원하지 않는 타입은 `recommended_instance_type`을 만들지 않습니다. 리포트 문구도 다운사이즈 확정이 아니라 검토 후보로 표현합니다.

## 8. 리포트와 알림

Markdown 리포트와 알림 요약은 각 finding마다 다음 정보를 표시합니다.

- resource_id
- resource_type
- finding_type
- severity
- confidence_score
- action_priority
- owner/project/environment/service
- estimated_monthly_savings
- safe_action
- Korean recommendation text

## 9. LLM의 역할

LLM은 finding을 생성하지 않습니다. LLM은 분석기가 만든 deterministic finding을 한국어 권고문으로 설명합니다.

LLM에 전달되는 정보는 finding의 제한된 요약 필드입니다. AWS raw response 전체는 전달하지 않습니다.

## 10. 안전 원칙

- EC2 stop, terminate, modify_instance_attribute API를 호출하지 않습니다.
- EBS delete_volume, create_snapshot API를 호출하지 않습니다.
- 비용, 점수, 우선순위는 rule analyzer와 pricing module에서만 계산합니다.
- 리포트는 운영자가 검토할 수 있는 후보와 안전 절차를 제공합니다.
