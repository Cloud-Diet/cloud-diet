# 변경 로그

## 2026-06-09

### 추가

- finding별 `confidence_score`를 0~100 범위로 계산하는 규칙 기반 점수 체계를 추가했습니다.
- finding별 `action_priority`를 `immediate_review`, `review`, `observe`, `excluded`로 분류합니다.
- EBS 미사용 finding에 `safe_action=snapshot_before_delete`와 단계별 `recommended_steps`를 추가했습니다.
- 태그 기반 `owner`, `project`, `environment`, `service` 추출을 추가했습니다.
- 로컬 가격표 기반 월 비용/절감액 계산 모듈 `app/pricing/price_estimator.py`를 추가했습니다.
- EC2 다운사이즈 검토 후보에 한해 `t3.large -> t3.medium -> t3.small -> t3.micro` 타입 제안을 추가했습니다.
- 샘플 데이터에 dev/prod/staging/test, protected tag, 가격 계산 가능/불가 케이스를 추가했습니다.
- 전체 기능 설명서 `docs/FEATURE_GUIDE.md`와 내부 파일 변경 내역 `docs/INTERNAL_CHANGES.md`를 추가했습니다.

### 변경

- Markdown 리포트와 알림 요약에 신뢰도, 우선순위, 담당/환경, 예상 절감액, 안전 조치를 표시하도록 개선했습니다.
- LLM 추천기는 rule analyzer가 만든 값만 설명하도록 입력 필드를 제한했습니다.
- README를 최신 핵심 기능 중심으로 재작성했습니다.
- `configs/rules.yaml`에 pricing 설정을 추가했습니다.

### 유지

- 실제 AWS 리소스를 변경하는 API 호출은 추가하지 않았습니다.
- 기존 finding `type` 값은 유지하고, 호환성을 위해 `finding_type`을 함께 추가했습니다.
- 기존 sample mode와 console notifier 흐름은 유지했습니다.
