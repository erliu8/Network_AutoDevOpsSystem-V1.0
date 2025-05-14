from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from core.services.device_service import DeviceService
import re
import time
import traceback
import os
import telnetlib

class DHCPConfigurator:
    def __init__(self, device_type, enterprise="", ip=None, username=None, password=None):
        """初始化DHCP配置器
        
        参数:
            device_type (str): 设备类型, 支持"huawei_telnet"
            enterprise (str): 企业名称，用于设备配置上下文，可选
            ip (str): 设备IP地址，可选，如果提供则直接使用
            username (str): 用户名，可选，如果提供则直接使用
            password (str): 密码，可选，如果提供则直接使用
        """
        print(f"初始化DHCP配置器: 设备类型={device_type}, 企业={enterprise}, IP={ip}")
        
        # 强制设置为huawei_telnet，仅支持华为Telnet
        self.device_type = "huawei_telnet"
        self.enterprise = enterprise
        
        # 存储设备信息
        if ip is not None:
            # 如果直接提供了设备信息，则使用这些信息
            print("使用直接提供的设备信息")
            self.device_info = {
                'ip': ip,
                'username': username or '1',  # 使用默认值1
                'password': password or '1'   # 使用默认值1
            }
            # 确保必要字段存在且非空
            required_fields = ['ip']
            for field in required_fields:
                if not self.device_info.get(field):
                    # 如果是必要字段，则记录错误并替换为默认值而不是抛出异常
                    print(f"[警告] 设备信息字段 '{field}' 为空，将使用默认值")
                    if field == 'ip':
                        # 对于IP，如果未提供则使用默认测试值
                        self.device_info['ip'] = '127.0.0.1'
            print(f"设备信息: IP={self.device_info.get('ip')}, 用户名={self.device_info.get('username')}")
        else:
            # 否则从系统获取设备信息
            print("从系统获取设备信息")
            self.device_info = self._get_device_info()
        
        # 如果没有找到设备信息，抛出异常
        if not self.device_info:
            raise ValueError(f"未找到设备信息: {device_type} - {enterprise}")
            
        # 确保设备信息包含必要的字段
        required_fields = ['ip', 'username', 'password']
        for field in required_fields:
            if field not in self.device_info:
                raise ValueError(f"设备信息缺少必要字段: {field}")
                
        print(f"设备信息: IP={self.device_info['ip']}, 用户名={self.device_info['username']}")
        
        # 存储最后执行的命令
        self.last_commands = []
    
    def _get_device_info(self):
        """获取设备信息"""
        try:
            # 返回华为Telnet命令集
            return {
                'command_set': {
                    'enter_config': 'system-view',
                    'exit_config': 'return',
                    'save_config': 'save',
                    'create_dhcp_pool': 'ip pool {pool_name}',
                    'set_network': 'network {network}',
                    'set_gateway': 'gateway-list {gateway}',
                    'set_dns': 'dns-list {dns}',
                    'set_domain': 'domain-name {domain}',
                    'set_lease': 'lease day {lease_days}',
                    'show_dhcp_pools': 'display ip pool'
                }
            }
        except Exception as e:
            print(f"获取设备信息时出错: {str(e)}")
            traceback.print_exc()
            # 默认返回基本的huawei命令集
            return {
                'command_set': {
                    'enter_config': 'system-view',
                    'exit_config': 'return',
                    'save_config': 'save',
                    'create_dhcp_pool': 'ip pool {pool_name}',
                    'set_network': 'network {network}',
                    'set_gateway': 'gateway-list {gateway}',
                    'set_dns': 'dns-list {dns}',
                    'set_domain': 'domain-name {domain}',
                    'set_lease': 'lease day {lease_days}',
                    'show_dhcp_pools': 'display ip pool'
                }
            }
        
    def configure_dhcp(self, pool_name, network, excluded=None, dns=None, gateway=None, lease_time=None, debug=False, domain=None):
        """配置DHCP服务
        
        Args:
            pool_name: DHCP地址池名称
            network: 网络地址，支持CIDR格式(192.168.1.0/24)或传统格式(192.168.1.0 255.255.255.0)
            excluded: 排除地址范围，可选
            dns: DNS服务器地址，可选
            gateway: 默认网关，可选
            lease_time: 租约时间，可选
            debug: 是否启用调试模式，可选
            domain: 域名，可选
            
        Returns:
            bool: 配置是否成功
        """
        # 检查参数有效性
        if not pool_name or not network:
            print(f"缺少必要参数: pool_name={pool_name}, network={network}")
            return False
        
        print(f"开始配置DHCP服务 - 地址池: {pool_name}, 网络: {network}")
        print(f"参数: 排除地址={excluded}, DNS={dns}, 网关={gateway}, 租约时间={lease_time}, 域名={domain}")
            
        # 处理网络地址格式
        network_cmd = None
        if '/' in network:  # CIDR格式
            ip, prefix = network.split('/')
            mask = self._prefix_to_mask(int(prefix))
            network_cmd = f'network {ip} mask {mask}'
        elif ' ' in network:  # 传统格式 "IP 掩码"
            ip, mask = network.split(' ', 1)
            network_cmd = f'network {ip} mask {mask}'
        else:  # 只有IP地址，使用外部传入的掩码
            network_cmd = f'network {network}'
            
        # 创建日志目录
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 设置日志文件
        log_file = os.path.join(log_dir, f"huawei_telnet_commands_{int(time.time())}.log")
        
        # 初始化命令记录列表
        self.last_commands = []
        
        # 为华为Telnet设备执行命令
        try:
            print("使用华为Telnet命令")
            # 提取域名
            domain_name = domain  # 优先使用直接传入的域名参数
            
            # 如果域名为空，尝试从dns字典中提取
            if not domain_name and isinstance(dns, dict):
                domain_name = dns.get('domain') or dns.get('domain_name')
                
            print(f"域名设置: {domain_name}")
            
            # 使用默认租约时间如果未提供
            if lease_time is None:
                lease_time = 3  # 默认3天
                
            commands = self._get_simplified_huawei_commands(
                pool_name, 
                network_cmd, 
                excluded, 
                dns, 
                gateway, 
                domain_name, 
                lease_time
            )
            success = self._try_execute_commands(commands, log_file, debug)
                
            # 记录执行结果
            print(f"DHCP配置{'成功' if success else '失败'}")
            
            return success
        except Exception as e:
            print(f"配置DHCP服务时出错: {str(e)}")
            traceback.print_exc()
            return False
    
    def _try_execute_commands(self, commands, log_file=None, debug=False):
        """尝试使用Telnet执行命令列表"""
        # 保存命令列表到日志
        print(f"执行 {len(commands)} 条命令，调试模式: {'开启' if debug else '关闭'}")
        self.last_commands = commands.copy()
        
        # 记录命令到日志文件
        if log_file:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("===== 将执行以下命令 =====\n")
                for i, cmd in enumerate(commands):
                    f.write(f"{i+1}. {cmd}\n")
                f.write("===== 命令列表结束 =====\n\n")
        
        # 保存实际执行的命令
        executed_commands = []
        
        # 如果是调试模式，仅打印命令而不执行
        if debug:
            print("调试模式: 不执行实际命令。命令列表:")
            for i, cmd in enumerate(commands):
                print(f"{i+1}. {cmd}")
            return True
        
        try:
            # 使用原生Telnet直接连接设备
            print(f"尝试Telnet连接设备: {self.device_info['ip']}")
            tn = telnetlib.Telnet(self.device_info['ip'], 23, timeout=15)  # 增加超时时间
            
            # 记录连接过程到日志
            logs = []
            
            # 等待登录提示并输入用户名
            resp = tn.read_until(b"Username:", timeout=10)
            logs.append(f"登录提示: {resp.decode('ascii', errors='ignore')}")
            
            tn.write(self.device_info['username'].encode('ascii') + b"\n")
            
            # 等待密码提示并输入密码
            resp = tn.read_until(b"Password:", timeout=10)
            logs.append(f"密码提示: {resp.decode('ascii', errors='ignore')}")
            
            tn.write(self.device_info['password'].encode('ascii') + b"\n")
            
            # 等待提示符
            resp = tn.read_until(b">", timeout=10)
            logs.append(f"登录响应: {resp.decode('ascii', errors='ignore')}")
            
            print(f"已成功连接到设备 {self.device_info['ip']}")
            
            # 执行每个命令
            all_outputs = []
            
            # 当前的命令模式
            current_mode = "normal"  # normal, system-view, dhcp-pool
            
            for cmd in commands:
                try:
                    executed_commands.append(cmd)  # 记录即将执行的命令
                    print(f"正在执行命令: {cmd}")
                    
                    # 发送命令
                    tn.write(cmd.encode('ascii') + b"\n")
                    
                    # 根据命令和当前模式决定要等待的提示符
                    if cmd == 'system-view':
                        current_mode = "system-view"
                        resp = tn.read_until(b"]", timeout=10)
                    elif cmd.startswith('ip pool'):
                        current_mode = "dhcp-pool"
                        resp = tn.read_until(b"]", timeout=10)
                    elif cmd == 'quit' and current_mode == "dhcp-pool":
                        current_mode = "system-view"
                        resp = tn.read_until(b"]", timeout=10)
                    elif cmd == 'quit' and current_mode == "system-view":
                        current_mode = "normal"
                        resp = tn.read_until(b">", timeout=10)
                    elif current_mode == "system-view":
                        resp = tn.read_until(b"]", timeout=10)
                    elif current_mode == "dhcp-pool":
                        resp = tn.read_until(b"]", timeout=10)
                    else:
                        resp = tn.read_until(b">", timeout=10)
                    
                    # 等待一小段时间，确保命令执行完成
                    time.sleep(0.5)
                    
                    output = resp.decode('ascii', errors='ignore')
                    all_outputs.append(output)
                    logs.append(f"命令 '{cmd}' 响应: {output}")
                    
                    print(f"命令响应: {output}")
                    
                    # 检查输出中是否有错误
                    if "Error" in output or "错误" in output or "Invalid" in output or "无效" in output:
                        print(f"执行命令 '{cmd}' 时出现错误: {output}")
                        # 继续执行，不中断
                        
                except Exception as e:
                    error_msg = f"执行命令 '{cmd}' 时出错: {str(e)}"
                    print(error_msg)
                    logs.append(error_msg)
                    # 继续执行，不中断
            
            # 完成配置后，显示DHCP池信息
            try:
                if current_mode != "normal":
                    # 如果不在normal模式，先返回到normal模式
                    while current_mode != "normal":
                        print("返回到normal模式...")
                        tn.write(b"quit\n")
                        resp = tn.read_until(b">", timeout=10)
                        current_mode = "normal"
                
                # 显示DHCP池信息
                print("获取DHCP池信息...")
                tn.write(b"display ip pool\n")
                resp = tn.read_until(b">", timeout=10)
                dhcp_info = resp.decode('ascii', errors='ignore')
                logs.append(f"DHCP池信息: {dhcp_info}")
                print(f"DHCP池信息: {dhcp_info}")
                
                # 保存配置
                print("保存配置...")
                tn.write(b"save\n")
                resp = tn.read_until(b"[Y/N]:", timeout=10)
                tn.write(b"Y\n")
                resp = tn.read_until(b">", timeout=20)
                save_result = resp.decode('ascii', errors='ignore')
                logs.append(f"保存配置结果: {save_result}")
                print(f"保存配置结果: {save_result}")
            except Exception as e:
                error_msg = f"执行后续操作时出错: {str(e)}"
                print(error_msg)
                logs.append(error_msg)
            
            # 关闭Telnet连接
            tn.close()
            print(f"已断开与设备 {self.device_info['ip']} 的Telnet连接")
            
            # 将日志写入文件
            if log_file:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write("\n===== 执行日志 =====\n")
                    for log_entry in logs:
                        f.write(f"{log_entry}\n")
                    
                    f.write("\n===== 命令执行结果 =====\n")
                    for i, (cmd, output) in enumerate(zip(commands, all_outputs)):
                        f.write(f"命令 {i+1}: {cmd}\n")
                        f.write(f"输出:\n{output}\n")
                        f.write("-" * 50 + "\n")
            
            # 保存执行的命令列表
            self.last_commands = executed_commands
            
            return True
            
        except Exception as e:
            error_msg = f"执行Telnet连接或命令时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            
            # 将错误附加到日志文件
            if log_file:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write("\n===== 执行错误 =====\n")
                    f.write(f"{error_msg}\n")
                    f.write(traceback.format_exc())
            
            return False
    
    def _get_simplified_huawei_commands(self, pool_name, network_cmd, excluded=None, dns=None, gateway=None, domain_name=None, lease_time=None):
        """获取简化的华为设备命令列表"""
        commands = [
            'system-view',
            f'ip pool {pool_name}'
        ]
        
        # 调整命令顺序: 先网关，再网络
        if gateway:
            commands.append(f'gateway-list {gateway}')
            
        # 添加网络命令
        commands.append(network_cmd)
        
        # 其他命令
        if excluded:
            if ' ' in excluded:
                start, end = excluded.split()
                commands.append(f'excluded-ip-address {start} {end}')
            else:
                commands.append(f'excluded-ip-address {excluded}')
                
        if dns:
            if isinstance(dns, str):
                commands.append(f'dns-list {dns}')
            elif isinstance(dns, list) and len(dns) > 0:
                # 处理DNS列表
                for dns_server in dns[:2]:  # 华为设备通常最多支持两个DNS服务器
                    commands.append(f'dns-list {dns_server}')
        
        # 添加域名配置 - 只有当提供了域名时才添加
        if domain_name:
            commands.append(f'domain-name {domain_name}')
        
        # 添加租约时间 - 始终添加租约时间
        if lease_time:
            # 确保租约时间是整数
            try:
                lease_days = int(lease_time)
                commands.append(f'lease day {lease_days}')
            except (ValueError, TypeError):
                print(f"警告: 租约时间 '{lease_time}' 不是有效的整数，将使用默认值3天")
                commands.append('lease day 3')
        else:
            # 默认3天租约
            commands.append('lease day 3')
            
        commands.append('quit')
        commands.append('quit')
        
        return commands
            
    def _prefix_to_mask(self, prefix):
        """将CIDR前缀转换为点分十进制掩码
        
        Args:
            prefix: CIDR前缀，如24
            
        Returns:
            str: 点分十进制掩码，如255.255.255.0
        """
        mask = (0xffffffff >> (32 - prefix)) << (32 - prefix)
        return '.'.join([str((mask >> (8 * i)) & 0xff) for i in range(3, -1, -1)])