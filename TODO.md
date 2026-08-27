# TODO

닫히지 않은 것만 적는다. 끝나면 지운다.

## 1. self-study 노트가 public 리포에 남아 있음

`notes/self-study/260826_Learning-while-you-sleep-...html` 은 `.gitignore` 규칙(`notes/self-study/**`)이 생기기 전인 `9b490b8` 에 이미 커밋돼서 추적 중이다. gitignore 는 추적 중인 파일을 되돌리지 못한다.

- [ ] `git rm --cached <파일>` → `build-notes-index.py` 재실행 → 커밋·푸시 (발행·목록에서 빠짐)
- [ ] 커밋 이력에서도 지울지 결정 — 지우려면 `git filter-repo` + force push (커밋 8개짜리 리포라 부담 작음)

앞으로 만들 self-study 노트는 문제없다 — gitignore 가 정상적으로 잡는다 (확인함).

## 2. CI 슬랙 전송 실전 검증

`slack.py` 자체는 검증됐다 (2026-08-26 수동 전송 성공). 검증 안 된 건 **워크플로가 새 노트를 골라 스크립트를 호출하는 구간**이다.

- [ ] 다음 노트를 푸시할 때 `slack` 잡 로그 확인 — 파일이 잡히는지, 전송되는지
- [ ] 실패하면 `gh run rerun --failed` 로 슬랙 잡만 재실행되는지도 같이 확인 (잡 분리의 목적)

## 3. 문서가 CI 전송을 모른다

`README.md` 와 `CLAUDE.md` 모두 `slack.py` 를 로컬에서 직접 돌리는 것으로만 설명한다. 지금은 푸시하면 CI 가 보낸다.

- [ ] 두 문서에 CI 경로와 리포 시크릿(`SLACK_BOT_TOKEN` · `SLACK_CHANNEL`) 설명 추가

## 4. actions v4 → v5

`pages.yml` 의 `ponytail:` 주석 참고. 2026-08-26 로그에서 Node 20 deprecated 경고, 러너가 Node 24 로 강제 실행 중이다.

- [ ] 실제로 깨지거나 v5 가 안정되면 `checkout` · `upload-pages-artifact` · `deploy-pages` 를 한꺼번에 올린다

## 하지 않기로 한 것

- **슬랙 재시도 루프** — 지금까지 실패 두 건은 빈 시크릿과 잡 결합이었고 둘 다 재시도로 안 고쳐진다. 실제 5xx·rate limit 을 보면 그때 넣는다.
- **Pages 워크플로 `gh run rerun`** — 같은 run 에 `github-pages` 아티팩트가 둘이 되어 `deploy-pages` 가 죽는다. 새 run 을 만들 것.
