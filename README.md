1) 데이터베이스 생성
    1.  터미널 접속
    2.  psql -U postgres;
    3.  CREATE DATABASE dalgona_db;
        CREATE ROLE dalgona_user WITH LOGIN PASSWORD <비밀번호>;
        CREATE SCHEMA IF NOT EXISTS dalgona_game AUTHORIZATION dalgona_user;

        -- 권한
        GRANT USAGE, CREATE ON SCHEMA dalgona_game TO dalgona_user;

    4.  터미널 종료후 다시 접속
    5.  cd (*/SQL)
    6.  psql -U postgres -d game -f setup.sql

    7.  pgAdmin4 실행(6번 오류시)
    8.  queryTool에서 setup.sql 명령어 붙여넣은 후 실행


2) 환경변수(.env) 변경
    1.  server 폴더에 .env 파일 수정 -> "postgresql+asyncpg://dalgona_user:<비밀번호>@<IP주소>:5432/dalgona_db"
    2.  DB_app 폴더에 .config 파일 수정 -> "postgresql+asyncpg://dalgona_user:<비밀번호>@<IP주소>:5432/dalgona_db"
    

3) 인증서 설정
    1.  Chocolatey 설치
    2.  cd <*/server/certs>
    3.  choco install mkcert -y
        mkcert -install
        mkcert <서버IP>

4) 방화벽 개방
    1.  PowerShell 실행
    2.  New-NetFirewallRule -DisplayName "Uvicorn 8001" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8001
    3.  New-NetFirewallRule -DisplayName "Uvicorn 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000

5) Unity 스크립트 수정
    1. AI_WebSocketClient.cs -> Ws Url 수정
    2. DB_WebSocketClient.cs -> Ws Url, Rest Base Url 수정


6) 서버 실행
    - DB서버
        uvicorn DB_app.main:app --host 0.0.0.0 --port 8001 --ssl-certfile "*\server\certs\192.168.55.82.pem" --ssl-keyfile  "*\server\certs\192.168.55.82-key.pem

    - AI서버
        uvicorn DB_app.main:app --host 0.0.0.0 --port 8002

    - WEBUI(선택)
        node.js 터미널 실행 ->
        cd */server/realtime-chart
        npm run dev
