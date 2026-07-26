# LoL 프로 대회 캘린더

LoL Esports 공식 API 기반 프로 대회 일정 캘린더. 리그별 필터, 월별/목록 뷰, 팀 검색.

- 페이지를 열 때마다 브라우저에서 공식 API를 직접 호출해 최신 일정으로 갱신
- `data.json` 스냅샷은 GitHub Actions가 매일 갱신 (API 장애 시 폴백)
- 시간은 보는 사람의 기기 시간대로 표시

로컬 갱신: `python fetch_data.py`
