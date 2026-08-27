# TODO

닫히지 않은 것만 적는다. 끝나면 지운다.

## 1. 슬랙 잡만 재실행되는지 미확인

워크플로가 새 노트를 골라 보내는 구간은 확인됐다 (2026-08-27 run 33030304908 · 33031483320, 두 잡 다 success, 링크 전송됨).

- [ ] 슬랙 잡이 실패하면 `gh run rerun --failed` 로 그 잡만 다시 도는지 — 잡 분리의 목적이 이거다. 실패 케이스가 안 나와서 아직 못 봤다

## 2. actions v4 → v5

`pages.yml` 의 `ponytail:` 주석 참고. 2026-08-26 로그에서 Node 20 deprecated 경고, 러너가 Node 24 로 강제 실행 중이다.

- [ ] 실제로 깨지거나 v5 가 안정되면 `checkout` · `upload-pages-artifact` · `deploy-pages` 를 한꺼번에 올린다

## 하지 않기로 한 것

- **기존 self-study 노트 1건 추적 해제** — `notes/self-study/260826_Learning-while-you-sleep-...html` 은 gitignore 규칙보다 먼저 커밋돼(`9b490b8`) 지금도 추적·발행 중이다. 인지하고 두기로 함. 앞으로 만들 노트는 gitignore 가 잡는다.
- **슬랙 재시도 루프** — 지금까지 실패 두 건은 빈 시크릿과 잡 결합이었고 둘 다 재시도로 안 고쳐진다. 실제 5xx·rate limit 을 보면 그때 넣는다.
- **Pages 워크플로 `gh run rerun`** — 같은 run 에 `github-pages` 아티팩트가 둘이 되어 `deploy-pages` 가 죽는다. 새 run 을 만들 것.
