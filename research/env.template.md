# Replication Environment Tech Spec

## [작성 방법]
1. 각 항목별 예시 내용 확인 후 선정하여 작성
2. 작성하지 않는 부분은 삭제
3. 각 항목별 작성 할 내용 없거나 'None' 인 경우 소항목 삭제
   - 필요한 것만 간략하게 작성하는 것이 최고!! 
4. 결과적으로 필요한 정보만 남도록 구성

---

## 💢예시 💢
## 대상 소프트웨어
- 제품명/버전
  - MediaWiki 1.43.0 
  - AbuseFilter 확장 1.43.0
- 배포방식: 소스 설치(LocalSettings.php)

## 시스템 환경
- OS: Ubuntu 22.04
- Web 서버: Apache 2.4
- PHP: 8.1
- DB: MariaDB 10.6

## 의존하는 구성요소
- 사용 확장: AbuseFilter, CheckUser
- PHP 모듈: pdo_mysql, mbstring

## 네트워크 환경
- 로컬 단일 서버로 구축 가능
- 포트: 80(HTTP), 3306(DB)

## PoC 실행 환경
- 공격자 클라이언트  
  - curl / BurpSuite 사용

## 이 외 추가 정보 작성

---

# 🫡🫡45번 줄부터 복붙해서 작성해주세요!!🫡🫡

---

# Replication Environment Tech Spec

## 대상 소프트웨어(Target Application Specification)

- 제품명/버전 :
  - 정확하게 취약점 나온 버전 / 패치 버전 등
- 배포 방식 : 
  예) Source install, Docker, Kubernetes, 패키지 설치 등
  - 설치 링크 혹은 설치 소스 첨부하면 좋을 듯!

---

## 시스템 환경(System Environment)

- OS 종류 및 버전 : 
  예) Ubuntu 22.04, Rocky Linux 9.3, Windows Server 2022 등
- Kernel 버전 (특히 Linux) : (있으면 적기)
- Web Server : 
  예) Apache / Nginx / IIS / Lighttpd → 버전 포함
- Database 종류 및 버전 : 
  예) MySQL / MariaDB / PostgreSQL / SQLite

---

## 의존하는 구성요소(Dependencies)
(1-day 취약점 분석에서 필요, 딱히 안나오면 Skip)

- Composer / pip / npm 등 의존성 리스트 : 
  예 ) AbuseFilter, CheckUser 등 작성
- 프레임워크 버전 : 
- Plugin/Extension 버전 : 
- ORM 및 DB 연결 방식 : 
  예) PDO, mysqli, SQLAlchemy Engine, Prisma 등

---

## 네트워크 환경(Network Topology)

- 로컬 단일 서버
- 서버 IP / 포트 구조 : 
  예) Web 80/443, DB 3306, API 8080 등
- Reverse Proxy 여부 : 
  예) Cloudflare / Nginx Reverse Proxy
- NAT · Bridge 등 가상화 네트워크 모드 (테스트 VM일 경우) : 

---

## PoC 실행 환경(PoC Execution Environment)
(피해자/공격자 가능할 시 둘 다 작성)

- 공격자 클라이언트
  예) Kali Linux 2024.x, curl 버전, Burp Suite Pro 2024.x
- 스크립트/툴 버전
  예) Python PoC 파일, curl, wget, ffuf, nuclei 등
- 브라우저 버전
  예) Chrome/Firefox 버전

---

## 이 외 필요한 조건

예:

- AbuseFilter API의 Protected Variables 접근 권한 체크가 비활성화된 상태
- JWT secret이 `default_secret`으로 설정되어 있음
- Anonymous user라도 `/api/checkmatch` 호출 가능
- CSRF token 검증이 Dispatcher 단계에서 스킵됨
