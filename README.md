# vps节点 一键脚本
```
wget -O multiplenode.sh https://raw.githubusercontent.com/ziqing888/multiplenode/main/multiplenode.sh && chmod +x multiplenode.sh && ./multiplenode.sh
```

# MultipleLite 插件多账号 脚本

MultipleLite Bot 是一个为 Multiple Lite 节点开发的自动化 PING 工具，支持多账户并行运行，同时支持自动代理和手动代理。

---

## 功能特点

- **多账户支持**：从 `accounts.txt` 文件加载多个账户，并为每个账户独立运行。
- **代理功能**：支持自动代理（从 GitHub 下载最新代理列表）和手动代理（从 `manual_proxy.txt` 文件加载）。
- **日志输出**：支持丰富的日志级别，包括信息、成功、警告、错误和调试，方便排查问题。
- **节点状态监控**：实时检查每个账户的节点运行状态，包括在线状态和累计运行时间。
- **定时 PING**：每隔 10 分钟向 Multiple Lite 发送一个保持活动的 PING 请求。

---

## 环境要求

### 系统要求
- Python 3.8 或更高版本

### 依赖库

在运行此程序前，请先安装以下依赖库：

```bash
pip install asyncio aiohttp aiohttp-socks eth-account fake-useragent pytz colorama halo
```
## 安装步骤
### 克隆项目仓库
```bash
git clone https://github.com/ziqing888/multiplenode.git
cd multiplenode
```
### 安装依赖
使用以下命令安装依赖：
```bash
pip install -r requirements.txt
```
### 准备账户文件
将所有以太坊私钥保存到 accounts.txt 文件中，每行一个私钥。例如：
```bash
0xabc123...
0xdef456...
```
### 准备代理文件（可选）
如果需要使用手动代理，请在项目根目录下创建一个 manual_proxy.txt 文件，并在其中添加代理地址（每行一个代理）。
```bash
http://username:password@proxy1.example.com:port
socks5://proxy2.example.com:port
```
### 运行程序
```bash
python3 main.py
```
程序运行后，会实时输出每个账户的状态，包括 PING 成功次数、节点在线状态和累计运行时间。
