# Cloud Diet 데이터 형식 문서

이 문서는 Cloud Diet 내부에서 사용하는 입력, 중간 산출물, 출력 파일 형식을 설명합니다.

## 입력 데이터

### AWS EC2 raw 입력

`app/collectors/aws_ec2_collector.py`는 boto3 `describe_instances` 응답 중 `Instances` 배열을 그대로 모읍니다.

간단한 예:

```json
{
  "InstanceId": "i-1234567890abcdef0",
  "InstanceType": "t3.large",
  "State": {
    "Name": "running"
  },
  "LaunchTime": "2026-05-01T01:00:00+00:00",
  "Tags": [
    {
      "Key": "Name",
      "Value": "api-server-prod"
    },
    {
      "Key": "Env",
      "Value": "prod"
    }
  ]
}
```

### AWS EBS raw 입력

`app/collectors/aws_ebs_collector.py`는 boto3 `describe_volumes` 응답 중 `Volumes` 배열을 그대로 모읍니다.

```json
{
  "VolumeId": "vol-1234567890abcdef0",
  "Size": 100,
  "State": "available",
  "VolumeType": "gp3",
  "CreateTime": "2026-04-20T01:00:00+00:00",
  "Attachments": [],
  "Tags": [
    {
      "Key": "Name",
      "Value": "old-test-volume"
    }
  ]
}
```

## 표준 리소스 모델

Normalizer 이후 모든 리소스는 공통 필드인 `resource_type`, `resource_id`, `region`, `tags`를 가집니다.

### EC2 표준 모델

```json
{
  "resource_type": "EC2",
  "resource_id": "i-1234567890abcdef0",
  "name": "api-server-prod",
  "region": "ap-northeast-2",
  "instance_type": "t3.large",
  "state": "running",
  "launch_time": "2026-05-01T10:00:00+09:00",
  "cpu_avg_14d": 7.8,
  "cpu_max_14d": 21.4,
  "memory_avg_14d": null,
  "estimated_monthly_cost": null,
  "tags": {
    "Name": "api-server-prod",
    "Env": "prod"
  }
}
```

필드 설명:

| 필드 | 타입 | 의미 |
|---|---|---|
| `resource_type` | string | 항상 `EC2` |
| `resource_id` | string | EC2 Instance ID |
| `name` | string/null | `Name` 태그 값 |
| `region` | string | AWS 리전 |
| `instance_type` | string | 인스턴스 타입 |
| `state` | string | `running`, `stopped` 등 |
| `launch_time` | string/null | 생성 시각 ISO 8601 |
| `cpu_avg_14d` | number/null | 최근 14일 CPU 평균 |
| `cpu_max_14d` | number/null | 최근 14일 CPU 최대 |
| `memory_avg_14d` | number/null | CloudWatch Agent 연동 전까지 null |
| `estimated_monthly_cost` | number/null | MVP에서는 null |
| `tags` | object | AWS 태그 |

### EBS 표준 모델

```json
{
  "resource_type": "EBS",
  "resource_id": "vol-1234567890abcdef0",
  "region": "ap-northeast-2",
  "state": "available",
  "size_gb": 100,
  "volume_type": "gp3",
  "create_time": "2026-04-20T10:00:00+09:00",
  "attached_instance_id": null,
  "detached_days": 18,
  "estimated_monthly_cost": null,
  "tags": {
    "Name": "old-test-volume"
  }
}
```

필드 설명:

| 필드 | 타입 | 의미 |
|---|---|---|
| `resource_type` | string | 항상 `EBS` |
| `resource_id` | string | EBS Volume ID |
| `region` | string | AWS 리전 |
| `state` | string | `available`, `in-use` 등 |
| `size_gb` | number | 볼륨 크기 |
| `volume_type` | string | gp3, gp2, io2 등 |
| `create_time` | string/null | 볼륨 생성 시각 |
| `attached_instance_id` | string/null | 연결된 EC2 ID |
| `detached_days` | number/null | 미연결 추정 일수 |
| `estimated_monthly_cost` | number/null | MVP에서는 null |
| `tags` | object | AWS 태그 |

## Finding 모델

Analyzer는 표준 리소스를 읽어 Finding을 생성합니다.

```json
{
  "severity": "medium",
  "type": "possible_overprovisioned_ec2",
  "resource_type": "EC2",
  "resource_id": "i-1234567890abcdef0",
  "reason": "최근 14일 평균 CPU 사용률이 7.8%로 낮습니다.",
  "evidence": {
    "cpu_avg": 7.8,
    "cpu_max": 21.4,
    "analysis_days": 14,
    "threshold_cpu_avg": 10.0,
    "threshold_cpu_max": 30.0
  },
  "recommended_action": "다운사이징 검토",
  "risk_checklist": [
    "피크 시간대 트래픽 확인",
    "배치 작업 및 예약 작업 여부 확인",
    "서비스 소유자와 변경 가능 시간 확인"
  ],
  "resource": {
    "resource_type": "EC2",
    "resource_id": "i-1234567890abcdef0"
  }
}
```

`severity` 값:

| 값 | 의미 |
|---|---|
| `high` | 우선 검토 필요 |
| `medium` | 일반적인 최적화 후보 |
| `low` | 추가 확인 후 검토 |
| `info` | 정보성 |

## 출력 파일 형식

### `outputs/resources_*.json`

표준 리소스 모델의 배열입니다. 수집 단계가 정상적으로 동작했는지 확인할 때 사용합니다.

```json
[
  {
    "resource_type": "EC2",
    "resource_id": "i-1234567890abcdef0",
    "state": "running"
  }
]
```

### `outputs/findings_*.json`

Finding 모델의 배열입니다. 어떤 룰이 어떤 리소스를 잡았는지 추적할 때 사용합니다.

```json
[
  {
    "severity": "high",
    "type": "unused_ebs_volume",
    "resource_type": "EBS",
    "resource_id": "vol-1234567890abcdef0"
  }
]
```

### `outputs/report_*.md`

운영자가 읽는 Markdown 리포트입니다. 탐지 이유, evidence, 권고문, 조치 전 확인 항목을 포함합니다.

## LLM 입력 형식

LLM에는 Finding 전체가 아니라 필요한 필드만 전달합니다.

```json
{
  "severity": "high",
  "type": "unused_ebs_volume",
  "resource_type": "EBS",
  "resource_id": "vol-1234567890abcdef0",
  "reason": "18일 동안 EC2 인스턴스에 연결되지 않은 EBS 볼륨입니다.",
  "evidence": {
    "detached_days": 18,
    "threshold_detached_days": 14,
    "state": "available",
    "size_gb": 100,
    "volume_type": "gp3"
  },
  "recommended_action": "삭제 또는 스냅샷 전환 검토",
  "risk_checklist": [
    "스냅샷 백업 필요 여부 확인",
    "최근 복구 작업 또는 테스트 작업에서 사용되는지 확인"
  ]
}
```

## 알림 메시지 예시

```text
[Cloud Diet] 일일 비용 최적화 후보 리포트
- 생성 시각: 2026-05-12 09:00
- 분석 기간: 최근 14일
- 탐지 건수: 2

1. EBS vol-1234567890abcdef0
- 심각도: high
- 유형: unused_ebs_volume
- 근거: 18일 동안 EC2 인스턴스에 연결되지 않은 EBS 볼륨입니다.
- 권고: 삭제 또는 스냅샷 전환 검토
- 확인 필요: 스냅샷 백업 필요 여부 확인, 최근 복구 작업 또는 테스트 작업에서 사용되는지 확인, 태그의 서비스/소유자 정보 확인
```

