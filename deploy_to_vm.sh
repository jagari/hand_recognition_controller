#!/bin/bash

# ====================================================================
# 🚀 God Hand Landing Page VM Deployment Automation Script
# ====================================================================

set -e

VM_IP="100.126.113.44"
PORT="8080"
LOCAL_DIR="download_page"
TAR_FILE="download_page.tar.gz"
CONF_FILE="nginx_download_page.conf"

echo "===================================================="
echo "  🖐️ God Hand 랜딩 페이지 학교 VM 배포 스크립트 가동"
echo "===================================================="
echo "대상 IP: $VM_IP"
echo "배포 포트: $PORT"
echo "===================================================="

# 1. VM SSH 정보 입력 받기
read -p "👤 VM SSH 계정명 입력 (기본: ubuntu): " SSH_USER
SSH_USER=${SSH_USER:-ubuntu}

read -p "🔑 SSH Private Key 파일 경로 (사용 안 하면 엔터): " SSH_KEY_PATH

SSH_OPT=""
SCP_OPT=""
if [ -n "$SSH_KEY_PATH" ]; then
    if [ -f "$SSH_KEY_PATH" ]; then
        SSH_OPT="-i $SSH_KEY_PATH"
        SCP_OPT="-i $SSH_KEY_PATH"
        echo "ℹ️ SSH Key 경로 설정 완료: $SSH_KEY_PATH"
    else
        echo "❌ 지정한 SSH Key 파일을 찾을 수 없습니다. 경로를 확인해 주세요."
        exit 1
    fi
fi

# 2. 로컬 웹 자산 압축
echo "📦 1. 로컬 웹 자산 압축 중 ($LOCAL_DIR -> $TAR_FILE)..."
if [ ! -d "$LOCAL_DIR" ]; then
    echo "❌ 에러: $LOCAL_DIR 디렉토리가 현재 위치에 존재하지 않습니다."
    exit 1
fi
tar -czf "$TAR_FILE" -C "$LOCAL_DIR" .
echo "✅ 압축 완료!"

# 3. Nginx 설정 임시 파일 생성
echo "⚙️ 2. Nginx 설정 파일 생성 중 ($CONF_FILE)..."
cat <<EOF > "$CONF_FILE"
server {
    listen $PORT default_server;
    listen [::]:$PORT default_server;

    root /var/www/download_page;
    index index.html;

    server_name _;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF
echo "✅ Nginx 설정 파일 로컬 생성 완료!"

# 4. VM 서버로 파일 전송 (SCP)
echo "📤 3. VM 서버의 /tmp 경로로 압축 파일 및 Nginx 설정 전송 중..."
scp $SCP_OPT "$TAR_FILE" "$CONF_FILE" "${SSH_USER}@${VM_IP}:/tmp/"
echo "✅ 파일 전송 성공!"

# 5. 원격 SSH 명령 실행 (Nginx 설치, 파일 구성 및 서비스 재시작)
# sudo 패스워드 입력을 받아야 하므로 ssh -t 옵션으로 pseudo-terminal 할당
echo "🛠️ 4. VM 서버 원격 패키지 설치 및 Nginx 배포 제어 가동..."
echo "ℹ️ 아래 실행 시 VM 서버의 패스워드(sudo 권한) 입력을 요구할 수 있습니다."

ssh -t $SSH_OPT "${SSH_USER}@${VM_IP}" "
    echo '👉 [VM] 시스템 업데이트 및 Nginx 설치 여부 점검...';
    sudo apt-get update && sudo apt-get install -y nginx;

    echo '👉 [VM] 배포 폴더 구성 및 웹 자산 압축 풀기...';
    sudo mkdir -p /var/www/download_page;
    sudo tar -xzf /tmp/$TAR_FILE -C /var/www/download_page;

    echo '👉 [VM] Nginx 설정 파일 배치 및 심볼릭 링크 연동...';
    sudo mv /tmp/$CONF_FILE /etc/nginx/sites-available/download_page;
    sudo ln -sf /etc/nginx/sites-available/download_page /etc/nginx/sites-enabled/;

    # 기본 default 포트 80 충돌 방지 및 8080 단독 포트 활성화를 위해 기존 설정 링크 제거
    sudo rm -f /etc/nginx/sites-enabled/default;

    echo '👉 [VM] Nginx 설정 무결성 점검...';
    sudo nginx -t;

    echo '👉 [VM] 8080 포트를 점유 중인 기존 프로세스(Python 등) 종료...';
    sudo fuser -k 8080/tcp || true
    sudo kill -9 \$(sudo lsof -t -i:8080) 2>/dev/null || true

    echo '👉 [VM] Nginx 서비스 재부팅...';
    sudo systemctl restart nginx;

    echo '👉 [VM] 방화벽(UFW) $PORT 포트 개방 허용...';
    sudo ufw allow $PORT/tcp || echo 'ℹ️ UFW 방화벽이 가동되지 않았거나 존재하지 않아 스킵합니다.';

    echo '👉 [VM] 임시 원격 파일 정리...';
    rm -f /tmp/$TAR_FILE;
    echo '🎉 [VM] 원격 웹 서버 배포 세팅이 성공적으로 끝났습니다!';
"

# 6. 로컬 임시 자산 정리
rm -f "$TAR_FILE" "$CONF_FILE"

echo "===================================================="
echo "🎉 랜딩 웹사이트 배포 완료!"
echo "접속 링크: http://${VM_IP}:${PORT}"
echo "===================================================="
