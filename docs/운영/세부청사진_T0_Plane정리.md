# 세부청사진 T0 · Plane 정리

> 상위: [청사진_가상데이터단계](청사진_가상데이터단계.md) §4 · 작성: 2026-10-27 팀장 · 상태: 착수 대기 (**최우선**, 다른 T와 병행)
> 사용자 요청 원문: "plane에이전트 활용해서 plane에 파일 나눠서 가독성 좋게 정리해줘."

| 항목 | 내용 |
|---|---|
| Plane | 워크스페이스 `hyonam-kim` · 프로젝트 LTGE "G코드 대비 가공오차 정량평가" · 항목 44개 |
| 담당 | Plane 담당 (Plane MCP 도구를 쓰는 worker, Opus 5.5, effort medium) |
| 기간 | T0a 2026-10-28 ~ 10-29 (페이지 ①–④, 항목 정리) · T0b 11-04 (G0 뒤 페이지 ⑤⑥ 채움) |
| 선행 | 메인이 `docs/운영/` 청사진 문서를 커밋·푸시한 뒤 시작 (페이지 링크가 살아 있어야 함) |
| 후행 | 모든 작업의 "Plane 반영" 단계 (청사진 §7 8단계)가 이 정리 결과 위에서 돕니다 |
| 산출물 | Plane 페이지 7개 · Plane 항목 44개 정리 · `docs/운영/plane/` 백업·검증 스냅숏 · `docs/운영/대조/T0_대조표.md` |

## 1. 목적

Plane을 처음 여는 사람이 **5분 안에** 과제 목표, 현재 결정, 작업 순서, 자기 할 일을 찾게 합니다.
원본은 저장소 문서입니다. Plane 페이지는 요약과 링크만 둡니다.
하드웨어 항목 삭제 뒤 남은 옛 표기 (없어진 선행 항목, 옛 µm 기준)를 걷어 내고, 비어 있는 상태·기간·모듈을 채웁니다.

## 2. 목표 (완료 기준)

| 번호 | 완료 기준 | 측정 방법 |
|---|---|---|
| P1 | 상위 페이지 1개 + 하위 페이지 6개 (①–⑥)가 있고, 하위 페이지가 상위 페이지 아래에 있음. 계층 기능이 없으면 제목 앞 번호 (`LTGE ①` …)와 상위 페이지 목차 링크로 대신함 | 페이지 스냅숏 (검증 명령 ③) |
| P2 | 모든 페이지 첫 줄에 `원본:` 링크와 `기준일:`이 있음. 페이지마다 4,000자 이하. 본문은 표 중심 | 검증 명령 ③ |
| P3 | 페이지의 저장소 링크가 모두 원격 브랜치에 실제로 있는 파일을 가리킴 (깨진 링크 0) | 검증 명령 ④ |
| P4 | 항목 44개 모두 상태가 부록 A 표와 같음 (빈 상태 0) | 검증 명령 ② |
| P5 | 상태가 ToDo·InProgress인 항목은 시작일·마감일이 부록 A 표와 같음. Backlog 항목의 날짜는 건드리지 않음 | 검증 명령 ② |
| P6 | 항목 44개 모두 모듈이 있음. 요소 항목은 요소 코드 첫 글자 모듈 (F0 → F, J0 → J). 마일스톤은 기존 관례 유지 | 검증 명령 ② |
| P7 | 항목 본문에서 삭제된 20개 항목 (A3 · B3–B7 · C1–C3 · C5–C8 · E1 · F2 · K2 · K3 · M0–M2)과 그 W번호를 가리키는 곳 0. 남은 곳은 부록 B 대체표대로 바꿈 | 검증 명령 ② (남은 적중은 팀장이 한 줄씩 판정) |
| P8 | 옛 표기 0: A2의 옛 기준 (층 높이 ±0.02 mm → 2–5 µm 중심)을 0.2–0.4 mm·Q ≤ 50/20 µm 기준으로, M4의 "E3 설계·출력"을 "E3 가상 시편 설계 + 시뮬레이터 생성"으로 고침. 그 밖의 옛 표기는 발견 목록과 처리 결과를 대조표에 | 검증 명령 ② + 팀장 열람 |
| P9 | 본문 구조 (Objective · Scope of Work · Completion Requirements · Assignees · Dependencies)가 정리 전후로 그대로임. 체크박스 개수가 줄지 않음 | 정리 전·후 스냅숏 비교 (검증 명령 ②) |
| P10 | 정리 전 백업 스냅숏과 정리 후 스냅숏이 저장소에 있음. 바뀐 항목마다 "무엇을 무엇으로" 한 줄 기록 | `docs/운영/plane/` 파일 확인 |

## 3. 페이지 구성

| 페이지 | 제목 (안) | 꼭 담을 것 | 원본 링크 |
|---|---|---|---|
| 상위 | LTGE 과제 안내 (2026-10-27 기준) | 한 줄 목표, 하위 페이지 목차 (링크), "원본은 저장소" 안내, 갱신 규칙 | 저장소 README · 중심주제 |
| ① | 과제 개요와 현재 결정 | 궁극 목표 (중심주제 §1), 10-27 결정 4가지 표 (측정 방식 · 교차검증 · 요구 0.2–0.4 mm · 하드웨어 작업 없음), M54 사양 한 줄 표, 다음 게이트 날짜 | 중심주제 · 청사진 §1 · M54 |
| ② | 운영 체계 | 팀장·worker 역할, 문서 체계 5층 표, 8단계 대조 절차 표, 판정 기호, 금지 명령 요약 | 청사진 §0 · §5 · §7 |
| ③ | 0단계 방법탐색 결과 | §000 선정표 (후보 · 비용 · Q · 0.2 mm · 0.4 mm), 선정 결론 2줄, 이전 선정 (§00 · §0)은 링크만 | 비교-선정 §000 |
| ④ | 작업 지도 | T0–T13 작업표 (작업 · Plane 항목 · 기간 · 선행 · 담당), 게이트 표 (G0 · G1 · G2 · M3 · M4 · M5), 모듈 → 항목 표 (A–K, 44개 전부) | 청사진 §4 · §6 |
| ⑤ | 하드웨어 데이터 명세 | T0a: "T1 진행 중, 11-03 동결 뒤 채움" 한 줄. T0b: 7묶음 표 (묶음 · 파일 · 필수 필드 수), 폴더 구조, 삭제 항목 대응 요약 | `docs/하드웨어-데이터-명세.md` |
| ⑥ | 측정 실패 사례 | T0a: "T2 진행 중, 10-30 마감" 한 줄. T0b: 심각도 상위 10개 표, 범주별 개수, 대책 요약 | `docs/측정-실패사례.md` |

- 페이지 첫 줄 형식: `원본: <GitHub 링크> · 기준일: 2026-10-28 · 담당: 팀장 (갱신은 저장소 먼저)`.
- 링크 기준: `https://github.com/dawnnam02/cv-lab/blob/claude/lidar-error-measurement-blueprint-vq1ofq/<경로>`.
- 저장소 문서를 통째로 붙여 넣지 않습니다. 요약 표 + 링크입니다.
- 한국어, 짧은 문장, 비교는 표. Plane 편집기에서 mermaid가 안 그려지면 표로 바꿉니다.

## 4. 항목 정리 규칙

| 대상 | 규칙 |
|---|---|
| Dependencies | 삭제된 항목을 가리키는 줄은 부록 B 대체표대로 바꿉니다. 대체할 것이 없으면 그 줄만 지웁니다 |
| 옛 기준·옛 표기 | P8의 두 곳은 반드시 고칩니다. 그 밖에 찾은 옛 표기는 고치기 전에 대조표에 목록을 쓰고, 명백한 것 (삭제 항목 이름, 옛 마일스톤 날짜)만 고칩니다. 판단이 필요한 것은 팀장에게 묻습니다 |
| 구조 | 제목 헤더 (Objective · Scope of Work · Completion Requirements · Assignees · Dependencies)와 체크박스는 그대로 둡니다. 문장만 고칩니다 |
| 제목 | 바꾸지 않습니다. `[M0][C0W번호][작업종류]` 형식 위반을 찾으면 대조표에 적고 팀장에게 보고만 합니다 |
| 상태·기간·모듈 | 부록 A 표대로 맞춥니다. 표와 Plane 값이 다르면 표를 따르고, 바꾸기 전 값은 백업 스냅숏에 남습니다 |
| 변경 메모 | 항목 본문에 변경 메모를 덧붙이지 않습니다 (가독성). 변경 기록은 저장소의 대조표와 스냅숏에 둡니다 |
| 다른 worker 작업 | 다른 worker가 D1–D5 · E3 · M3–M6 · A2 본문에 "가상 데이터 기준" 안내를 붙이는 중입니다. **그 작업이 끝났다고 메인이 확인해 주기 전에는 이 11개 항목 본문을 고치지 않습니다.** 상태·기간·모듈만 먼저 바꿉니다. 끝난 뒤 고칠 때도 그 안내 문단은 지우거나 옮기지 않습니다 |

## 5. 단계

| 단계 | 날짜 | 할 일 | 끝난 표시 |
|---|---|---|---|
| S1 | 10-28 | 시작 확인 (§8). Plane MCP 도구 중 페이지 생성·수정·상위 지정 도구가 있는지 확인 | 대조표 "시작 확인" 절 |
| S2 | 10-28 | **정리 전 백업**: 항목 44개 전부를 `docs/운영/plane/LTGE_items_20261028_before.json`로 저장 (§6.1 형식). 기존 페이지 목록도 `LTGE_pages_20261028_before.json` | 파일 2개, 항목 수 44 |
| S3 | 10-28 | 사라진 W번호 20개를 1–62의 빈 번호로 확인하고, 남은 42개 + W063·W064의 W번호 ↔ 요소 코드 대응표를 대조표에 씀 (청사진 §4.1 W번호 칸을 채울 재료) | 대응표 44행 |
| S4 | 10-28 | 상태·기간·모듈을 부록 A대로 맞춤 (44개) | 검증 명령 ② 의 P4–P6 통과 |
| S5 | 10-28 ~ 10-29 | 본문 정리: 삭제 항목 참조 (부록 B), A2·M4 옛 표기, 그 밖 옛 표기 목록. 다른 worker 작업 끝남 확인 전에는 그 11개 항목 제외 | 검증 명령 ② 의 P7–P9 적중 목록 |
| S6 | 10-29 | 페이지 상위 1 + ①–④ 작성, ⑤⑥은 진행 중 한 줄 | 검증 명령 ③④ 통과 |
| S7 | 10-29 | 정리 후 스냅숏 `LTGE_items_20261029_after.json`, `LTGE_pages_20261029_after.json`. 바뀐 항목마다 한 줄 기록 `docs/운영/plane/T0_변경기록.md` | 파일 3개 |
| S8 | 10-29 | 종료 대조표 작성 → 팀장 검증 | 점검일지 판정 |
| S9 (T0b) | 11-04 | G0 통과 뒤 페이지 ⑤⑥ 채움, ④의 진행 상태 갱신, 다시 스냅숏 | 검증 명령 ③④ 재통과 |

## 6. 검증

### 6.1 스냅숏 형식

항목 스냅숏 (`LTGE_items_<날짜>_<before 또는 after 또는 check>.json`): JSON 배열, 항목마다

```json
{"seq": 63, "name": "[M0][C0W063][SW] F0. 하드웨어 데이터 명세", "state": "In Progress",
 "start_date": "2026-10-27", "target_date": "2026-11-03", "module": "F. 데이터 획득",
 "description": "<본문 HTML 또는 텍스트 그대로>"}
```

페이지 스냅숏 (`LTGE_pages_<날짜>_<…>.json`): JSON 배열, 페이지마다 `{"name": …, "parent": 상위 페이지 이름 또는 null, "text": 본문 텍스트}`.

**검증용 스냅숏 (`_check`)은 메인이 Plane에서 따로 받아 저장합니다.** worker가 만든 `_after` 스냅숏만으로 판정하지 않습니다.

### 6.2 검증 명령 (Git Bash에 그대로 붙여 넣기)

① 파일 확인

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && ls -la docs/운영/plane/ && PYTHONIOENCODING=utf-8 python -c "import json,glob; [print(f, len(json.load(open(f,encoding='utf-8')))) for f in sorted(glob.glob('docs/운영/plane/*.json'))]"
```

② 항목 상태·기간·모듈·옛 참조 (검증용 스냅숏 기준)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import json,re,glob
chk=sorted(glob.glob('docs/운영/plane/LTGE_items_*_check.json'))[-1]
bef=sorted(glob.glob('docs/운영/plane/LTGE_items_*_before.json'))[0]
items=json.load(open(chk,encoding='utf-8')); old={i['seq']:i for i in json.load(open(bef,encoding='utf-8'))}
bp=open('docs/운영/세부청사진_T0_Plane정리.md',encoding='utf-8').read().split('## 부록 A. 항목별 목표 상태')[-1].split('## 부록 B')[0]
tgt={m[0]:m[1:] for m in re.findall(r'^\| ([A-K]\d|M[3-6]) \| (\w+) \| ([\d-]+|-) \| ([\d-]+|-) \| ([^|]+?) \|',bp,re.M)}
norm=lambda s:(s or '').replace(' ','').lower()
print('검증 스냅숏',chk,'/ 항목',len(items),'/ 목표표',len(tgt))
code=lambda n:(re.search(r'(?:^|\]\s*)([A-K]\d|M[3-6])\b',n) or [None,None])[1]
bad=[]
for i in items:
    c=code(i['name']); t=tgt.get(c)
    if not t: bad.append((i['seq'],'목표표에 없음',i['name'][:40])); continue
    st,sd,td,mod=t
    if norm(i.get('state'))!=norm(st): bad.append((c,'상태',i.get('state'),st))
    if st!='Backlog' and (i.get('start_date')!=sd or i.get('target_date')!=td): bad.append((c,'기간',i.get('start_date'),i.get('target_date'),sd,td))
    if not i.get('module'): bad.append((c,'모듈 빈칸'))
    elif mod.strip()!='기존 유지' and not i['module'].strip().startswith(mod.strip()): bad.append((c,'모듈',i['module'],mod))
print('P4–P6 불일치',len(bad)); [print(' ',b) for b in bad]
gone={n for n in range(1,63) if n not in {i['seq'] for i in items}}
print('사라진 W번호',len(gone),sorted(gone))
pat=re.compile(r'(?<![\[\w])(A3|B[3-7]|C[1-3]|C[5-8]|E1|F2|K2|K3)\.|(?<![\[\w])(M[0-2])(?![\w\]])')
stale=['E3 설계·출력','2–5 µm','2~5 µm','±0.02 mm']
hits=[]
for i in items:
    d=i.get('description') or ''
    hits+=[(i['seq'],'W'+w) for w in re.findall(r'C0W0*(\d+)',d) if int(w) in gone]
    hits+=[(i['seq'],m.group(0)) for m in pat.finditer(d)]
    hits+=[(i['seq'],s) for s in stale if s in d]
print('P7·P8 적중 (팀장이 한 줄씩 판정)',len(hits)); [print(' ',h) for h in hits[:60]]
cb=lambda d:len(re.findall(r'type="checkbox"|data-checked|- \[[ x]\]',d or ''))
hd=lambda d:[h for h in ['Objective','Scope of Work','Completion Requirements','Assignees','Dependencies'] if h in (d or '')]
p9=[(i['seq'],cb(old[i['seq']].get('description')),cb(i.get('description'))) for i in items if i['seq'] in old and (cb(i.get('description'))<cb(old[i['seq']].get('description')) or hd(i.get('description'))!=hd(old[i['seq']].get('description')))]
print('P9 구조·체크박스 감소',p9)
EOF
```

③ 페이지 구성 (검증용 스냅숏 기준)

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && PYTHONIOENCODING=utf-8 python - <<'EOF'
import json,glob
pg=json.load(open(sorted(glob.glob('docs/운영/plane/LTGE_pages_*_check.json'))[-1],encoding='utf-8'))
top=[p for p in pg if '과제 안내' in p['name']]
print('페이지',len(pg),'/ 상위',[p['name'] for p in top])
for p in pg:
    head=p['text'].strip().splitlines()[0] if p['text'].strip() else ''
    print(p['name'][:30],'| 상위:',p.get('parent'),'| 글자',len(p['text']),'| 원본·기준일',('원본:' in head and '기준일:' in head),'| 4000자 이하',len(p['text'])<=4000)
EOF
```

④ 페이지 링크가 원격 브랜치에 있는 파일인지

```bash
cd "/c/Users/dawnn/OneDrive/바탕 화면/CV/cv-lab" && git fetch -q origin && PYTHONIOENCODING=utf-8 python - <<'EOF'
import json,glob,re,subprocess,urllib.parse
B='claude/lidar-error-measurement-blueprint-vq1ofq'
pg=json.load(open(sorted(glob.glob('docs/운영/plane/LTGE_pages_*_check.json'))[-1],encoding='utf-8'))
files=set(subprocess.run(['git','-c','core.quotepath=false','ls-tree','-r','--name-only','origin/'+B],capture_output=True,text=True,encoding='utf-8').stdout.splitlines())
links=set()
for p in pg: links|=set(re.findall(r'github\.com/dawnnam02/cv-lab/blob/'+re.escape(B)+r'/([^\s)#"\'<>]+)',p['text']))
bad=[l for l in links if urllib.parse.unquote(l) not in files]
print('링크',len(links),'/ 깨진 링크',bad)
EOF
```

판정: ② 불일치 0, 적중은 모두 "정당한 언급"으로 팀장 판정, P9 빈 목록. ③ 7개 페이지 모두 True. ④ 깨진 링크 빈 목록.

### 6.3 팀장 표본 검사

- 정리 후 항목 5개를 무작위로 골라 Plane 화면 (또는 스냅숏)에서 전후 본문을 나란히 읽습니다. 뜻이 바뀐 문장, 지워진 체크박스가 없는지 봅니다.
- 페이지 ①–④를 처음 보는 사람 입장에서 읽고 "목표 · 현재 결정 · 다음 게이트 · 내 할 일"을 5분 안에 찾는지 확인합니다.
- 페이지 ③의 선정표 숫자를 비교-선정 §000 원문과 한 칸씩 대조합니다.

## 7. 금지 사항

- 항목을 지우거나 새로 만들지 않습니다 (T2용 항목 신설은 본인 결정 대기). 상태를 Cancelled로 바꾸지 않습니다 (본인만 가능).
- 항목 제목을 바꾸지 않습니다. LTGE 밖의 프로젝트·워크스페이스를 건드리지 않습니다.
- 다른 worker의 "가상 데이터 기준" 안내 문단을 지우거나 옮기지 않습니다. 그 11개 항목 본문은 메인 확인 전 손대지 않습니다.
- 숫자를 지어내지 않습니다. 페이지의 모든 숫자는 저장소 원본에서 옮기고, 원본에 없는 숫자는 쓰지 않습니다.
- 저장소에서는 `docs/운영/plane/`과 `docs/운영/대조/T0_대조표.md`만 만듭니다. 다른 저장소 파일은 고치지 않습니다.
- V2 미커밋 파일 (`scripts/method_screening/*`, `tests/test_method_screening.py`, `docs/0_방법탐색/결과_v3/`)을 고치거나 git으로 되돌리지 않습니다. `git add`·`commit`·`push`·`stash`·`checkout -- .`·`restore`·`clean`을 쓰지 않습니다.
- 백업 스냅숏 (S2) 없이 항목을 고치지 않습니다.

## 8. 시작 시 확인 항목

`docs/운영/대조/T0_대조표.md`의 "시작 확인" 절에 적고 시작합니다.

- [ ] `git pull` 결과, 브랜치, `git status --short` (V2 미커밋 파일 기준선)
- [ ] 원격 브랜치에 `docs/운영/청사진_가상데이터단계.md`가 있는지 (`git ls-tree origin/<브랜치> docs/운영/`). 없으면 메인에게 커밋을 요청하고 기다립니다
- [ ] Plane 연결: 워크스페이스 `hyonam-kim`, 프로젝트 LTGE 찾기, 항목 수 44 확인
- [ ] Plane MCP에 페이지 생성·수정·상위 지정 도구가 있는지. 없으면 페이지 부분은 멈추고 팀장에게 보고 (항목 정리는 계속)
- [ ] 프로젝트의 상태 이름 목록 (Backlog · Todo · In Progress · Done · Cancelled 등 실제 표기)과 모듈 이름 목록
- [ ] 다른 worker의 "가상 데이터 기준" 본문 작업이 끝났는지 메인에게 확인한 결과
- [ ] 목표 P1–P10을 자기 말로 한 줄씩

## 9. 종료 대조표 양식

```markdown
## 종료 대조 (2026-10-29 HH:MM)

| 목표 항목 | 결과 | 근거 위치 | 판정 |
|---|---|---|---|
| P1 페이지 계층 | 상위 1 + 하위 6 | 페이지 스냅숏 · 명령 ③ | ○ |
| P2 첫 줄·글자 수 | 7/7 | 명령 ③ | |
| P3 깨진 링크 | 0 | 명령 ④ | |
| P4 상태 | 44/44 일치 | 명령 ② | |
| P5 기간 | ToDo·InProgress n개 일치 | 명령 ② | |
| P6 모듈 | 44/44 | 명령 ② | |
| P7 삭제 항목 참조 | 적중 n건, 모두 처리 | 명령 ② · T0_변경기록.md | |
| P8 옛 표기 | A2 · M4 고침, 그 밖 n건 | T0_변경기록.md | |
| P9 구조 보존 | 체크박스 감소 0 | 명령 ② | |
| P10 백업·기록 | before · after · 변경기록 | docs/운영/plane/ | |

W번호 ↔ 요소 코드 대응표: (44행)
검증 명령 실행 결과: (붙여 넣기)
남은 문제: (없으면 "없음")
```

## 부록 A. 항목별 목표 상태

청사진 §4.1 일정과 같습니다. 상태 이름은 Plane 실제 표기에 맞추되 뜻은 이 표를 따릅니다. Backlog 행의 `-`는 "날짜를 건드리지 않음"입니다. 모듈 칸은 모듈 이름의 첫 글자입니다.

| 코드 | 상태 | 시작 | 마감 | 모듈 | 작업 |
|---|---|---|---|---|---|
| A1 | ToDo | 2027-02-02 | 2027-02-05 | A | T13 |
| A2 | ToDo | 2027-02-02 | 2027-02-05 | A | T13 |
| B1 | ToDo | 2026-11-04 | 2026-11-24 | B | T3 |
| B2 | ToDo | 2026-11-04 | 2026-11-24 | B | T3 |
| C4 | ToDo | 2026-11-25 | 2026-12-04 | C | T7 |
| D1 | ToDo | 2026-11-25 | 2026-12-01 | D | T8 |
| D2 | ToDo | 2026-12-02 | 2026-12-08 | D | T8 |
| D3 | ToDo | 2026-12-09 | 2026-12-12 | D | T8 |
| D4 | ToDo | 2026-12-09 | 2026-12-13 | D | T8 |
| D5 | ToDo | 2026-12-13 | 2026-12-15 | D | T8 |
| E2 | ToDo | 2026-11-04 | 2026-11-24 | E | T3 |
| E3 | ToDo | 2026-11-02 | 2026-11-06 | E | T5 |
| F0 | InProgress | 2026-10-27 | 2026-11-03 | F | T1 |
| F1 | ToDo | 2026-11-25 | 2026-12-04 | F | T7 |
| F3 | ToDo | 2026-11-04 | 2026-11-10 | F | T6 |
| G1 | ToDo | 2026-11-04 | 2026-11-08 | G | T4 |
| G2 | ToDo | 2026-11-09 | 2026-11-11 | G | T4 |
| G3 | ToDo | 2026-11-12 | 2026-11-15 | G | T4 |
| G4 | ToDo | 2026-11-16 | 2026-11-17 | G | T4 |
| G5 | Backlog | - | - | G | 보류 |
| H1 | ToDo | 2026-12-02 | 2026-12-08 | H | T9 |
| H2 | ToDo | 2026-12-02 | 2026-12-08 | H | T9 |
| H3 | ToDo | 2026-12-09 | 2026-12-15 | H | T9 |
| H4 | ToDo | 2026-12-09 | 2026-12-22 | H | T9 |
| H5 | ToDo | 2026-12-16 | 2026-12-28 | H | T10 |
| H6 | Backlog | - | - | H | T10 선택 |
| H7 | Backlog | - | - | H | T10 선택 |
| H8 | ToDo | 2027-01-12 | 2027-02-01 | H | T12 |
| I1 | ToDo | 2027-01-12 | 2027-02-01 | I | T12 |
| I2 | ToDo | 2027-01-12 | 2027-02-01 | I | T12 |
| I3 | ToDo | 2026-12-29 | 2027-01-11 | I | T11 |
| J0 | ToDo | 2026-11-04 | 2026-11-24 | J | T3 |
| J1 | ToDo | 2026-11-04 | 2026-11-10 | J | T6 |
| J2 | ToDo | 2026-11-04 | 2026-11-10 | J | T6 |
| J3 | ToDo | 2026-12-16 | 2026-12-28 | J | T10 |
| J4 | ToDo | 2026-12-16 | 2026-12-28 | J | T10 |
| K1 | ToDo | 2027-02-02 | 2027-02-05 | K | T13 |
| K4 | ToDo | 2027-02-02 | 2027-02-05 | K | T13 |
| K5 | ToDo | 2027-02-02 | 2027-02-05 | K | T13 |
| K6 | Backlog | - | - | K | 보류 |
| M3 | ToDo | 2026-12-28 | 2026-12-28 | 기존 유지 | T10 게이트 |
| M4 | ToDo | 2027-01-11 | 2027-01-11 | 기존 유지 | T11 게이트 |
| M5 | ToDo | 2027-02-01 | 2027-02-01 | 기존 유지 | T12 게이트 |
| M6 | Backlog | - | - | 기존 유지 | 다음 단계 |

## 부록 B. 삭제 항목 → 대체 참조표

| 삭제 항목 | 대체 참조 | 이유 |
|---|---|---|
| A3 가공 공정 | F0 (W063) | 프린터·재료·슬라이서 정보는 데이터 명세의 메타데이터 필드로 옮겨 감 |
| B3 상용 vs 자작 | 선행 줄 삭제 (비교-선정 §000 링크로 대신) | 10-27 결정으로 끝남 |
| B4 카메라 · B5 렌즈 · B6 레이저 · B7 필터 | J0 (W064) · F0 (W063) | 시뮬레이터의 광학 모델과 명세의 광학 필드가 대신함 |
| C1 스캔 이동 장치 | J0 (W064) · F0 (W063) | 프린터 축 위치는 위치 로그로 대신함 |
| C2 측정 시점 | F0 (W063) | 측정 시점은 메타데이터 필드 (`meta.timing`)와 본인 결정 D-04로 정함 |
| C3 지그·기준 마커 | D4 · E3 | 교정 판과 마커는 가상 교정과 가상 시편에서 다룸 |
| C5 주변광 · C6 온도 · C7 진동 | J0 (W064) | 시뮬레이터의 실패 요인으로 넣음 (T2 문서 연결) |
| C8 레이저 안전 | 선행 줄 삭제 | 가상 단계에 해당 없음. 실측 전환 때 다시 엶 |
| E1 표면 광학 | J0 (W064) | 시뮬레이터의 표면 산란 모델로 대신함 |
| F2 획득 파라미터 | F0 (W063) | 노출·게인·ROI 등은 명세 필드로 대신함 |
| K2 역할 | 선행 줄 삭제 (운영 청사진 §5 링크로 대신) | worker 배치표가 대신함 |
| K3 예산 | 선행 줄 삭제 (비교-선정 §000 링크로 대신) | 예산 검토 끝남 |
| M0 | F0 (W063) | 옛 "사양표 확정" 대신 G0 게이트 (11-03, 명세·실패사례 동결) |
| M1 · M2 | D5 | 옛 교정·단차 기준은 가상 교정 검증 (G2 게이트, 12-15)으로 대신함 |
