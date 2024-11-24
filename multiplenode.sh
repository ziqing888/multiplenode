#!/bin/bash
set -e  


GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${YELLOW}显示 LOGO...${NC}"
curl -s https://raw.githubusercontent.com/ziqing888/logo.sh/main/logo.sh | bash
echo -e "${GREEN}LOGO 加载完成！${NC}"

echo "开始自动安装 Multiple Network 节点..."
sleep 5


echo "检测系统架构..."
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    CLIENT_URL="https://cdn.app.multiple.cc/client/linux/x64/multipleforlinux.tar"
elif [[ "$ARCH" == "aarch64" ]]; then
    CLIENT_URL="https://cdn.app.multiple.cc/client/linux/arm64/multipleforlinux.tar"
else
    echo -e "${RED}不支持的系统架构: $ARCH${NC}"
    exit 1
fi


echo -e "${GREEN}从 $CLIENT_URL 下载客户端文件...${NC}"
wget $CLIENT_URL -O multipleforlinux.tar


echo -e "${GREEN}正在解压安装包...${NC}"
tar -xvf multipleforlinux.tar

cd multipleforlinux


echo -e "${GREEN}设置必要的文件权限...${NC}"
chmod +x multiple-cli
chmod +x multiple-node


echo -e "${GREEN}配置系统 PATH...${NC}"
echo "PATH=\$PATH:$(pwd)" >> ~/.bashrc
source ~/.bashrc


echo -e "${GREEN}设置目录权限...${NC}"
chmod -R 755 .


echo -e "${YELLOW}请输入账户信息绑定节点：${NC}"
read -p "请输入您的 IDENTIFIER（账户标识）： " IDENTIFIER
read -p "请输入您的 PIN（密码）： " PIN


echo -e "${GREEN}启动节点程序...${NC}"
nohup ./multiple-node > output.log 2>&1 &


echo -e "${GREEN}绑定账户信息...${NC}"
./multiple-cli bind --bandwidth-download 100 --identifier "$IDENTIFIER" --pin "$PIN" --storage 200 --bandwidth-upload 100


echo -e "${GREEN}安装完成！${NC}"
echo -e "${YELLOW}如需更多帮助，请运行 ./multiple-cli --help 查看可用命令。${NC}"
