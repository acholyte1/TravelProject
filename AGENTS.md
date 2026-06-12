# Codex 실행 환경 주의사항

- 로컬 PowerShell에서는 Python 3.14.5 사용 가능
- Codex 샌드박스에서는 `AppData\Local\Python\bin` 접근 제한 발생
- Codex 작업 시 내장 Python 3.12.13 절대 경로 사용:
  `C:\Users\acholyte\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- `PATH` 재설정만으로는 해결되지 않을 수 있음
