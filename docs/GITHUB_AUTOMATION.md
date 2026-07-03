# GitHub PR 자동화 설정

이 문서는 `vocast` 저장소에서 **PR 리뷰 → CI → 충돌 처리 → auto-merge** 흐름을 쓰기 위한 설정입니다.

## 저장소에 포함된 것

| 파일 | 역할 |
|------|------|
| `.github/workflows/ci.yml` | PR/push 시 smoke test 실행 |
| `.github/workflows/pr-automation.yml` | PR 브랜치를 `main`과 sync 시도 + auto-merge 활성화 |
| `tests/` | 설정/metadata 포맷 검증 |

## 사용자가 GitHub에서 직접 해야 하는 것

### 1. Auto-merge 켜기 (필수)

1. GitHub → `sukoji/vocast` → **Settings**
2. **General** → **Pull Requests**
3. **Allow auto-merge** 체크
4. (권장) **Automatically delete head branches** 체크

### 2. Branch protection 설정 (필수)

1. **Settings** → **Branches** → **Add branch protection rule**
2. Branch name pattern: `main`
3. 아래 항목 활성화:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging**
     - Required check: `test` (CI workflow job name)
   - (권장) **Require branches to be up to date before merging**
4. Save

> Free/private repo 정책에 따라 일부 옵션은 GitHub Team 이상에서만 보일 수 있습니다.

### 3. Bugbot / AI 리뷰 연결 (권장)

Cursor Bugbot을 쓰려면:

1. Cursor → Settings → Integrations → **GitHub**
2. `sukoji/vocast` 저장소에 Bugbot GitHub App 설치
3. PR 생성 시 자동 리뷰 코멘트 생성

Bugbot 없이도 CI + auto-merge는 동작합니다.

### 4. Actions 권한 확인 (필수)

1. **Settings** → **Actions** → **General**
2. **Workflow permissions**
   - **Read and write permissions** 선택
   - (권장) **Allow GitHub Actions to create and approve pull requests** 체크

`pr-automation.yml`이 PR 브랜치 업데이트와 auto-merge를 하려면 write 권한이 필요합니다.

### 5. Collaborator PR 흐름

외부 기여자 PR 흐름:

1. contributor가 fork → PR 생성
2. **CI** 자동 실행
3. **Bugbot** (설치 시) 자동 리뷰
4. CI green + conflict 없음 → **auto-merge** 대기
5. conflict 있으면 PR 코멘트로 알림 → contributor 또는 maintainer가 해결

fork PR은 보안상 `GITHUB_TOKEN` write 권한이 제한될 수 있습니다.  
이 경우 maintainer가 **Update branch** 버튼으로 수동 sync 후 merge하세요.

## 동작 요약

```text
PR opened
  → CI (tests/)
  → (optional) Bugbot review
  → pr-automation: merge main into PR branch (가능할 때)
  → pr-automation: enable auto-merge (squash)
  → branch protection 조건 충족 시 자동 merge
```

## 충돌 자동 해결 한계

- 단순 fast-forward/merge 가능한 경우: workflow가 `main`을 PR에 merge
- 코드 의미 충돌: 자동 해결하지 않음 → PR 코멘트 + 수동 해결 필요
- 복잡한 충돌은 Cursor Agent(babysit)로 PR checkout 후 해결 가능

## 로컬 확인

```bash
cd vocast
pip install -e .
pip install pytest pyyaml
pytest -q tests/
```
