import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from eth_account import Account
from eth_account.messages import encode_defunct
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import Fore, Style, init
import json, random, os, pytz, signal, sys
from halo import Halo

# 初始化 colorama
init(autoreset=True)

# =========================
# 日志记录模块
# =========================

import logging

class Logger:
    def __init__(self, timezone="Asia/Shanghai"):
        self.logger = logging.getLogger("MultipleLiteBot")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.timezone = timezone  # 定义时区

        # 定义日志级别到中文的映射
        self.level_map = {
            'info': '信息',
            'warn': '警告',
            'error': '错误',
            'success': '成功',
            'debug': '调试'
        }

    def log(self, level, message, value=''):
        now = get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone=self.timezone)
        level_lower = level.lower()
        level_cn = self.level_map.get(level_lower, '信息')
        colors = {
            '信息': Fore.CYAN + Style.BRIGHT,
            '警告': Fore.YELLOW + Style.BRIGHT,
            '错误': Fore.RED + Style.BRIGHT,
            '成功': Fore.GREEN + Style.BRIGHT,
            '调试': Fore.MAGENTA + Style.BRIGHT
        }
        color = colors.get(level_cn, Fore.WHITE)
        level_tag = f"[ {level_cn} ]"
        timestamp = f"[ {now} ]"
        formatted_message = f"{Fore.CYAN + Style.BRIGHT}[ MultipleLiteBot ]{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}{timestamp}{Style.RESET_ALL} {color}{level_tag}{Style.RESET_ALL} {message}"
        
        if value:
            if isinstance(value, dict) or isinstance(value, list):
                try:
                    serialized = json.dumps(value, ensure_ascii=False)
                    formatted_value = f" {Fore.GREEN}{serialized}{Style.RESET_ALL}" if level_cn != '错误' else f" {Fore.RED}{serialized}{Style.RESET_ALL}"
                except Exception as e:
                    self.error("序列化日志值时出错:", str(e))
                    formatted_value = f" {Fore.RED}无法序列化的值{Style.RESET_ALL}"
            else:
                if level_cn == '错误':
                    formatted_value = f" {Fore.RED}{value}{Style.RESET_ALL}"
                elif level_cn == '警告':
                    formatted_value = f" {Fore.YELLOW}{value}{Style.RESET_ALL}"
                else:
                    formatted_value = f" {Fore.GREEN}{value}{Style.RESET_ALL}"
            formatted_message += formatted_value

        self.logger.log(getattr(logging, level_upper(level_cn), logging.INFO), formatted_message)

    def info(self, message, value=''):
        self.log('info', message, value)

    def warn(self, message, value=''):
        self.log('warn', message, value)

    def error(self, message, value=''):
        self.log('error', message, value)

    def success(self, message, value=''):
        self.log('success', message, value)

    def debug(self, message, value=''):
        self.log('debug', message, value)

def level_upper(level_cn):
    """辅助函数，将中文级别转换为 logging 模块的级别名"""
    mapping = {
        '信息': 'INFO',
        '警告': 'WARNING',
        '错误': 'ERROR',
        '成功': 'INFO',  # 成功映射为 INFO
        '调试': 'DEBUG'
    }
    return mapping.get(level_cn, 'INFO')

logger = Logger()

# =========================
# 辅助函数模块
# =========================

def get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone="Asia/Shanghai"):
    """获取当前时间的字符串表示"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime(format)

async def delay(seconds):
    """延迟执行"""
    await asyncio.sleep(seconds)

async def save_to_file(filename, data):
    """将数据保存到文件，每条数据占一行"""
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            if isinstance(data, (dict, list)):
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            else:
                f.write(str(data) + '\n')
        logger.info(f"数据已保存到 {filename}")
    except Exception as e:
        logger.error(f"保存数据到 {filename} 时失败:", str(e))

async def read_file(path_file):
    """读取文件并返回非空行的列表"""
    try:
        if not os.path.exists(path_file):
            logger.warn(f"文件 {path_file} 不存在。")
            return []
        with open(path_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        logger.error(f"读取文件 {path_file} 时出错:", str(e))
        return []

def new_agent(proxy=None):
    """根据代理类型创建代理字典"""
    if proxy:
        if proxy.startswith('http://') or proxy.startswith('https://'):
            return proxy
        elif proxy.startswith('socks4://') or proxy.startswith('socks5://'):
            return proxy
        else:
            logger.warn(f"不支持的代理类型: {proxy}")
            return None
    return None

# =========================
# API 模块
# =========================

ua = FakeUserAgent()
headers = {
    "Accept": "application/json",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": ua.random
}

def make_headers(token=None, origin=None, referer=None, content_type='application/json'):
    """生成请求头"""
    hdr = headers.copy()
    hdr['Content-Type'] = content_type
    if origin:
        hdr['Origin'] = origin
    if referer:
        hdr['Referer'] = referer
    if token:
        hdr['Authorization'] = f'Bearer {token}'
    return hdr

async def user_dashboard_login(session, address, message, signature, proxy=None, retries=3):
    """用户仪表盘登录"""
    url = "https://api.app.multiple.cc/WalletLogin"
    data = json.dumps({"walletAddr": address, "message": message, "signature": signature})
    headers = make_headers(
        token=None,
        origin="https://www.app.multiple.cc",
        referer="https://www.app.multiple.cc/",
        content_type="application/json"
    )
    for attempt in range(retries):
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with session.post(url=url, headers=headers, data=data) as response:
                response.raise_for_status()
                result = await response.json()
                return result['data']['token']
        except (Exception, ClientResponseError) as e:
            if attempt < retries - 1:
                logger.warn(f"用户仪表盘登录失败，重试 {attempt + 1}/{retries}...")
                await asyncio.sleep(3)
            else:
                logger.error("用户仪表盘登录时失败:", str(e))
                return None

async def user_extension_login(session, dashboard_token, proxy=None, retries=3):
    """用户扩展登录"""
    url = "https://api.app.multiple.cc/ChromePlugin/Login"
    headers = make_headers(
        token=dashboard_token,
        origin="chrome-extension://ciljbjmmdhnhgbihlcohoadafmhikgib",
        referer=None,
        content_type="application/json"
    )
    for attempt in range(retries):
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with session.post(url=url, headers=headers, json={}) as response:
                response.raise_for_status()
                result = await response.json()
                return result['data']['token']
        except (Exception, ClientResponseError) as e:
            if attempt < retries - 1:
                logger.warn(f"用户扩展登录失败，重试 {attempt + 1}/{retries}...")
                await asyncio.sleep(3)
            else:
                logger.error("用户扩展登录时失败:", str(e))
                return None

async def user_information(session, extension_token, proxy=None, retries=3):
    """获取用户信息"""
    url = "https://api.app.multiple.cc/ChromePlugin/GetInformation"
    headers = make_headers(token=extension_token)
    for attempt in range(retries):
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with session.get(url=url, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()
                return result['data']
        except (Exception, ClientResponseError) as e:
            if attempt < retries - 1:
                logger.warn(f"获取用户信息失败，重试 {attempt + 1}/{retries}...")
                await asyncio.sleep(3)
            else:
                logger.error("获取用户信息时失败:", str(e))
                return None

async def send_keepalive(session, extension_token, proxy=None, retries=3):
    """发送保持活动的PING"""
    url = "https://api.app.multiple.cc/ChromePlugin/KeepAlive"
    headers = make_headers(
        token=extension_token,
        origin="chrome-extension://ciljbjmmdhnhgbihlcohoadafmhikgib",
        referer=None,
        content_type="application/x-www-form-urlencoded"
    )
    for attempt in range(retries):
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with session.post(url=url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except (Exception, ClientResponseError) as e:
            if attempt < retries - 1:
                logger.warn(f"发送PING失败，重试 {attempt + 1}/{retries}...")
                await asyncio.sleep(3)
            else:
                logger.error("发送PING时失败:", str(e))
                return None

# =========================
# 主程序类
# =========================

class MultipleLite:
    def __init__(self) -> None:
        self.proxies = []
        self.proxy_index = 0
        self.accounts = []
        self.timezone = "Asia/Shanghai"  # 设置时区为北京时间

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def welcome(self):
        welcome_message = f"""
{Fore.GREEN + Style.BRIGHT}自动PING {Fore.BLUE + Style.BRIGHT}Multiple Lite 节点 - 机器人
{Fore.GREEN + Style.BRIGHT}加入我们： {Fore.YELLOW + Style.BRIGHT}电报频道：https://t.me/ksqxszq
"""
        print(welcome_message)

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_auto_proxies(self):
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
        try:
            async with self.session.get(url=url, timeout=ClientTimeout(total=20)) as response:
                response.raise_for_status()
                content = await response.text()
                with open('proxy.txt', 'w') as f:
                    f.write(content)

                self.proxies = content.splitlines()
                if not self.proxies:
                    logger.error("下载的代理列表中未找到任何代理。")
                    return
                
                logger.success("代理已成功下载。", f"加载了 {len(self.proxies)} 个代理。")
                logger.info("-" * 75)
                await asyncio.sleep(3)
        except Exception as e:
            logger.error("加载代理时失败:", str(e))
            return []
        
    async def load_manual_proxy(self):
        try:
            if not os.path.exists('manual_proxy.txt'):
                logger.warn("未找到代理文件 'manual_proxy.txt'。")
                return

            with open('manual_proxy.txt', "r") as f:
                proxies = f.read().splitlines()

            self.proxies = proxies
            logger.success("手动代理已加载。", f"加载了 {len(self.proxies)} 个代理。")
            logger.info("-" * 75)
            await asyncio.sleep(3)
        except Exception as e:
            logger.error("加载手动代理时失败:", str(e))
            self.proxies = []

    def check_proxy_schemes(self, proxy):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxy.startswith(scheme) for scheme in schemes):
            return proxy
        return f"http://{proxy}"  # 如果代理未包含协议，可默认添加 http://

    def get_next_proxy(self):
        if not self.proxies:
            logger.error("当前无可用代理！")
            return None

        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.check_proxy_schemes(proxy)
        
    def hide_account(self, account):
        hide_account = account[:3] + '*' * 3 + account[-3:]
        return hide_account
    
    def generate_address(self, account: str):
        try:
            account_obj = Account.from_key(account)
            address = account_obj.address
            return address
        except Exception as e:
            logger.error("生成地址失败:", str(e))
            return None
        
    def generate_message(self, address: str):
        timestamp = datetime.now().astimezone(pytz.timezone(self.timezone))
        nonce = int(timestamp.timestamp() * 1000)
        message = (
            f"www.multiple.cc 想让您使用您的以太坊账户登录：{address}\n\t     \n消息:\n"
            f"网站: www.multiple.cc\n钱包地址: {address}\n时间戳: {timestamp}\nNonce: {nonce}"
        )
        return message

    def generate_signature(self, account: str, message: str):
        try:
            encoded_message = encode_defunct(text=message)
            signed_message = Account.sign_message(encoded_message, private_key=account)
            signature = signed_message.signature.hex()
            return signature
        except Exception as e:
            logger.error("生成签名失败:", str(e))
            return None
    
    async def proxy_questions(self):
        while True:
            try:
                print(f"{Fore.WHITE+Style.BRIGHT}1. 使用自动代理运行{Style.RESET_ALL}")
                print(f"{Fore.WHITE+Style.BRIGHT}2. 使用手动代理运行{Style.RESET_ALL}")
                print(f"{Fore.WHITE+Style.BRIGHT}3. 不使用代理运行{Style.RESET_ALL}")
                choose = int(input(f"{Fore.WHITE+Style.BRIGHT}请选择 [1/2/3] -> {Style.RESET_ALL}").strip())

                if choose in [1, 2, 3]:
                    proxy_type = (
                        "自动代理" if choose == 1 else 
                        "手动代理" if choose == 2 else 
                        "无代理"
                    )
                    logger.success(f"已选择使用{proxy_type}运行。")
                    await asyncio.sleep(1)
                    return choose
                else:
                    logger.warn("请输入1、2或3。")
            except ValueError:
                logger.warn("输入无效。请输入数字（1、2或3）。")

    async def user_log(self, session: ClientSession, address: str, extension_token: str, proxy=None):
        while True:
            user = await user_information(session, extension_token, proxy)
            if user:
                running_time = user.get('totalRunningTime', 0)
                is_online = user.get('isOnline', False)
                status = "节点已连接" if is_online else "节点未连接"
                color = Fore.GREEN if is_online else Fore.RED

                formatted_time = self.format_seconds(running_time)

                logger.info(
                    f"[ 账户: {self.hide_account(address)} ] 状态: {color}{status}{Style.RESET_ALL} | "
                    f"运行时间: {formatted_time}"
                )
            else:
                logger.error(
                    f"[ 账户: {self.hide_account(address)} ] 状态: 获取用户节点信息失败"
                )
            await asyncio.sleep(random.randint(600, 610))  # 10分钟后再次检查

    async def process_accounts(self, account: str, use_proxy: bool):
        ping_count = 1
        proxy = None
        if use_proxy:
            proxy = self.get_next_proxy()

        address = self.generate_address(account)
        if not address:
            logger.error(
                f"[ 账户: {self.hide_account(account)} ] 状态: 生成地址失败。请检查您的私钥。"
            )
            return

        message = self.generate_message(address)
        if not message:
            logger.error(
                f"[ 账户: {self.hide_account(address)} ] 状态: 生成消息失败。请检查您的私钥。"
            )
            return

        signature = self.generate_signature(account, message)
        if not signature:
            logger.error(
                f"[ 账户: {self.hide_account(address)} ] 状态: 生成签名失败。请检查您的私钥。"
            )
            return

        dashboard_token = None
        while dashboard_token is None:
            dashboard_token = await user_dashboard_login(self.session, address, message, signature, proxy)
            if not dashboard_token:
                logger.error(
                    f"[ 账户: {self.hide_account(address)} ] 状态: 获取仪表盘令牌失败。"
                )

                if not use_proxy:
                    return
                
                logger.info("尝试使用下一个代理...")
                await asyncio.sleep(1)
                
                proxy = self.get_next_proxy()
                continue

            logger.success(
                f"[ 账户: {self.hide_account(address)} ] 状态: 获取仪表盘令牌成功。代理: {proxy}"
            )
            
            extension_token = await user_extension_login(self.session, dashboard_token, proxy)
            if not extension_token:
                logger.error(
                    f"[ 账户: {self.hide_account(address)} ] 状态: 获取扩展令牌失败。"
                )
                return
            
            logger.success(
                f"[ 账户: {self.hide_account(address)} ] 状态: 获取扩展令牌成功。代理: {proxy}"
            )
            
            # 创建一个独立的任务来持续记录用户状态
            asyncio.create_task(self.user_log(self.session, address, extension_token, proxy))

            while True:
                logger.info("尝试发送PING...", "")
    
                send_ping = await send_keepalive(self.session, extension_token, proxy)
                if send_ping and send_ping.get('success', False):
                    logger.success(
                        f"[ 账户: {self.hide_account(address)} ] 状态: PING {ping_count} 成功。代理: {proxy}"
                    )
                else:
                    logger.error(
                        f"[ 账户: {self.hide_account(address)} ] 状态: PING {ping_count} 失败。代理: {proxy}"
                    )
                    if use_proxy:
                        proxy = self.get_next_proxy()
    
                ping_count += 1

                logger.info("等待10分钟后进行下一次PING...", "")
                await asyncio.sleep(random.randint(600, 610))  # 10分钟后再次发送PING

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            use_proxy_choice = await self.proxy_questions()

            use_proxy = False
            if use_proxy_choice in [1, 2]:
                use_proxy = True

            # 创建一个全局的 ClientSession，供所有任务使用
            timeout = ClientTimeout(total=60)
            connector = ProxyConnector.from_url(self.get_next_proxy()) if use_proxy and self.proxy_index < len(self.proxies) else None
            self.session = ClientSession(timeout=timeout, connector=connector)

            while True:
                self.clear_terminal()
                self.welcome()
                logger.info(f"账户总数: {len(accounts)}")
                logger.info("-" * 75)

                if use_proxy and use_proxy_choice == 1:
                    await self.load_auto_proxies()
                elif use_proxy and use_proxy_choice == 2:
                    await self.load_manual_proxy()
                
                tasks = []
                for account in accounts:
                    account = account.strip()
                    if account:
                        tasks.append(self.process_accounts(account, use_proxy))
                        
                # 并发执行所有账户的任务
                await asyncio.gather(*tasks)
                await asyncio.sleep(10)
        except FileNotFoundError:
            logger.error("错误: 'accounts.txt' 文件未找到。")
        except Exception as e:
            logger.error("错误:", str(e))
        finally:
            await self.shutdown()

    async def shutdown(self):
        """优雅地关闭程序"""
        current_time = get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone=self.timezone)
        exit_message = (
            f"{Fore.CYAN + Style.BRIGHT}[ {current_time} ]{Style.RESET_ALL} "
            f"{Fore.WHITE + Style.BRIGHT}| {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ 退出 ] MultipleLite 节点机器人已退出{Style.RESET_ALL}"
        )
        print(exit_message)
        # 取消所有挂起的任务
        tasks = asyncio.all_tasks(loop=asyncio.get_event_loop())
        for task in tasks:
            task.cancel()
        # 等待任务取消
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass
        # 关闭会话
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        sys.exit(0)

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.shutdown()))

# =========================
# 运行主程序
# =========================

if __name__ == "__main__":
    bot = MultipleLite()
    bot.setup_signal_handlers()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        asyncio.run(bot.shutdown())
    except Exception as e:
        logger.error("程序运行时出错:", str(e))
        sys.exit(1)
