# 내부 파일 변경 내역

## app/analyzers/rule_analyzer.py

- EC2/EBS finding에 `confidence_score`, `action_priority`, `reason_codes`, `finding_type`을 추가했습니다.
- EC2 finding에 `current_instance_type`, `recommended_instance_type`, `recommendation_basis`를 추가했습니다.
- EBS finding에 `safe_action=snapshot_before_delete`와 `recommended_steps`를 추가했습니다.
- 태그에서 담당자, 프로젝트, 환경, 서비스 정보를 추출해 finding에 포함합니다.
- protected tag(prod, production, critical)가 있으면 우선순위를 `excluded`로 낮춥니다.
- pricing 모듈을 호출해 예상 비용과 절감액을 finding에 결합합니다.

## app/pricing/price_estimator.py

- 새로 추가한 로컬 가격 추정 모듈입니다.
- EC2는 현재 타입과 권장 타입의 시간당 가격 및 월 사용 시간을 곱해 월 비용을 계산합니다.
- EBS는 볼륨 크기와 GB-month 가격을 곱해 월 비용을 계산합니다.
- 가격 정보가 없으면 비용 필드를 `None`으로 유지하고 안내 문구를 추가합니다.

## app/reporters/markdown_reporter.py

- Markdown 리포트를 우선순위 섹션별로 묶어 출력합니다.
- 각 finding에 심각도, 신뢰도, 액션 우선순위, 담당/프로젝트/환경/서비스, 예상 절감액, 안전 조치를 표시합니다.
- Slack/Discord/Console 요약 메시지도 새 핵심 필드를 포함하도록 수정했습니다.

## app/recommenders/llm_recommender.py

- LLM system prompt와 user prompt를 갱신해 입력에 없는 비용, 절감액, 우선순위, 신뢰도를 생성하지 않도록 제한했습니다.
- LLM 비활성 또는 실패 시 fallback 권고문이 EBS 안전 검토와 EC2 다운사이즈 검토를 명확히 설명합니다.

## app/normalizers/resource_normalizer.py

- AWS raw tag에서 `owner`, `project`, `environment`, `service` 메타데이터를 정규화된 resource JSON에 추가합니다.

## app/config.py

- 기본 rule 설정에 `pricing` 섹션을 추가했습니다.
- 가격 추정은 환경 변수가 아니라 `rules.yaml` 병합 결과를 사용합니다.

## configs/rules.yaml

- `pricing.currency`, `pricing.monthly_hours`, `pricing.ec2_hourly_prices`, `pricing.ebs_gb_month_prices`를 추가했습니다.

## configs/sample_resources.json

- 낮은 평균/최대 CPU EC2, 평균 CPU만 낮은 EC2, prod EC2, dev/test/staging EC2를 포함했습니다.
- 30일 이상 미연결 EBS, critical/backup/prod 태그 EBS, 가격 정보가 없는 EBS를 포함했습니다.
- 샘플 모드에서 신뢰도, 우선순위, 태그 추출, 비용 계산 성공/실패를 모두 확인할 수 있습니다.

## tests/

- `tests/test_rule_analyzer.py`에 신뢰도, 우선순위, 안전 조치, 가격 계산, unsupported instance type 테스트를 추가했습니다.
- `tests/test_pricing.py`를 추가해 가격 추정 모듈을 독립 검증합니다.
- `tests/test_markdown_reporter.py`를 새 리포트 필드 기준으로 갱신했습니다.
