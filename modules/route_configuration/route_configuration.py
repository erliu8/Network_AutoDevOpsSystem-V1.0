import re
import time
import threading
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from PyQt5.QtCore import QObject, pyqtSignal

# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class RouteConfigOperator(QObject):
    """路由配置操作类，负责与设备交互并执行路由配置命令"""
    
    # 定义信号
    config_status = pyqtSignal(str, bool, str)  # 设备IP, 是否成功, 消息
    command_output = pyqtSignal(str, str)       # 设备IP, 命令输出
    
    def __init__(self, ip, username, password, device_name="", device_type=""):
        super().__init__()
        self.device_info = {
            'device_type': 'huawei_telnet',
            'ip': ip,
            'username': username,
            'password': password,
            'port': 23,
            'timeout': 10,
            'conn_timeout': 15
        }
        self.device_name = device_name
        self.device_type = device_type
        self.connection = None
        self.is_router = "路由器" in device_type if device_type else False
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
    
    def connect_device(self):
        """连接到设备"""
        try:
            self.connection = ConnectHandler(**self.device_info)
            return True
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            self.config_status.emit(self.device_info['ip'], False, f"连接失败: {str(e)}")
            return False
        except Exception as e:
            self.config_status.emit(self.device_info['ip'], False, f"未知错误: {str(e)}")
            return False
    
    def disconnect_device(self):
        """断开设备连接"""
        if self.connection:
            self.connection.disconnect()
            self.connection = None
    
    def execute_command(self, command, expect_string=None):
        """执行单个命令并返回结果"""
        try:
            if not self.connection and not self.connect_device():
                return None
            
            if expect_string:
                output = self.connection.send_command_timing(
                    command,
                    strip_prompt=False,
                    strip_command=False
                )
            else:
                output = self.connection.send_command(
                    command,
                    strip_prompt=False,
                    strip_command=False
                )
            
            self.command_output.emit(self.device_info['ip'], output)
            return output
        except Exception as e:
            self.config_status.emit(self.device_info['ip'], False, f"执行命令失败: {str(e)}")
            return None
    
    def configure_static_route(self, dest_network, next_hop, distance=None):
        """配置静态路由"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._configure_static_route_thread,
            args=(dest_network, next_hop, distance),
            name=f"StaticRoute-{self.device_info['ip']}",
            module="路由配置模块"
        )
        return True
    
    def _configure_static_route_thread(self, dest_network, next_hop, distance=None):
        """在线程中执行静态路由配置"""
        try:
            # 只有在连接失败时才返回False
            if not self.connection and not self.connect_device():
                return False
            
            # 处理CIDR格式的网络地址
            if "/" in dest_network:
                addr, mask_bits = dest_network.split("/")
                # 转换CIDR掩码为点分十进制
                mask = self._cidr_to_mask(int(mask_bits))
                command = f"ip route-static {addr} {mask} {next_hop}"
            else:
                # 非CIDR格式，默认使用24位掩码(255.255.255.0)
                command = f"ip route-static {dest_network} 255.255.255.0 {next_hop}"
            
            if distance:
                command += f" preference {distance}"
            
            # 记录将要执行的命令
            self.command_output.emit(self.device_info['ip'], f"执行命令: {command}")
            
            # 进入系统视图
            self.connection.send_command_timing("system-view")
            
            # 执行配置命令并获取输出
            output = self.connection.send_command_timing(command)
            
            # 检查输出中是否有错误信息
            if "Error" in output or "错误" in output:
                self.config_status.emit(
                    self.device_info['ip'], 
                    False, 
                    f"静态路由配置失败: {output}"
                )
                return False
            
            # 保存配置
            self.connection.send_command_timing("return")
            save_output = self.connection.send_command_timing("save")
            if "Y/N" in save_output:
                self.connection.send_command_timing("y")
            
            self.config_status.emit(
                self.device_info['ip'], 
                True, 
                f"静态路由配置成功: {dest_network} -> {next_hop}"
            )
            return True
        except Exception as e:
            self.config_status.emit(
                self.device_info['ip'], 
                False, 
                f"静态路由配置失败: {str(e)}"
            )
            return False
        finally:
            self.disconnect_device()
    
    def configure_rip(self, version, networks):
        """配置RIP路由协议"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._configure_rip_thread,
            args=(version, networks),
            name=f"RIPConfig-{self.device_info['ip']}",
            module="路由配置模块"
        )
        return True
    
    def _configure_rip_thread(self, version, networks):
        """在线程中执行RIP配置"""
        try:
            if not self.connection and not self.connect_device():
                return False
            
            # 进入系统视图
            self.connection.send_command_timing("system-view")
            
            # 创建RIP进程
            self.connection.send_command_timing("rip")
            
            # 设置版本
            if version == 2:
                self.connection.send_command_timing("version 2")
            
            # 添加网络
            for network in networks:
                self.connection.send_command_timing(f"network {network}")
            
            # 退出RIP配置
            self.connection.send_command_timing("quit")
            
            # 保存配置
            self.connection.send_command_timing("return")
            save_output = self.connection.send_command_timing("save")
            if "Y/N" in save_output:
                self.connection.send_command_timing("y")
            
            self.config_status.emit(
                self.device_info['ip'], 
                True, 
                f"RIP配置成功: 版本{version}, 网络: {', '.join(networks)}"
            )
            return True
        except Exception as e:
            self.config_status.emit(
                self.device_info['ip'], 
                False, 
                f"RIP配置失败: {str(e)}"
            )
            return False
        finally:
            self.disconnect_device()
    
    def configure_ospf(self, process_id, area_id, networks):
        """配置OSPF路由协议"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._configure_ospf_thread,
            args=(process_id, area_id, networks),
            name=f"OSPFConfig-{self.device_info['ip']}",
            module="路由配置模块"
        )
        return True
    
    def _configure_ospf_thread(self, process_id, area_id, networks):
        """在线程中执行OSPF配置"""
        try:
            if not self.connection and not self.connect_device():
                return False
            
            # 进入系统视图
            self.connection.send_command_timing("system-view")
            
            # 创建OSPF进程
            self.connection.send_command_timing(f"ospf {process_id}")
            
            # 配置区域和网络
            self.connection.send_command_timing(f"area {area_id}")
            for network in networks:
                # 解析网络地址和掩码
                if "/" in network:
                    addr, mask_bits = network.split("/")
                    # 转换CIDR掩码为反掩码
                    wildcard = self._cidr_to_wildcard(int(mask_bits))
                    self.connection.send_command_timing(f"network {addr} {wildcard}")
                else:
                    self.connection.send_command_timing(f"network {network} 0.0.0.0")
            
            # 退出OSPF配置
            self.connection.send_command_timing("quit")
            
            # 保存配置
            self.connection.send_command_timing("return")
            save_output = self.connection.send_command_timing("save")
            if "Y/N" in save_output:
                self.connection.send_command_timing("y")
            
            self.config_status.emit(
                self.device_info['ip'], 
                True, 
                f"OSPF配置成功: 进程{process_id}, 区域{area_id}"
            )
            return True
        except Exception as e:
            self.config_status.emit(
                self.device_info['ip'], 
                False, 
                f"OSPF配置失败: {str(e)}"
            )
            return False
        finally:
            self.disconnect_device()
    
    def configure_bgp(self, as_number, router_id, neighbors, networks):
        """配置BGP路由协议"""
        try:
            if not self.is_router:
                self.config_status.emit(
                    self.device_info['ip'], 
                    False, 
                    "只有路由器设备支持BGP配置"
                )
                return False
                
            if not self.connection and not self.connect_device():
                return False
            
            # 进入系统视图
            self.connection.send_command_timing("system-view")
            
            # 创建BGP进程
            self.connection.send_command_timing(f"bgp {as_number}")
            
            # 配置路由器ID
            if router_id:
                self.connection.send_command_timing(f"router-id {router_id}")
            
            # 配置邻居
            for neighbor in neighbors:
                if isinstance(neighbor, dict):
                    # 格式: {"ip": "x.x.x.x", "as": 100} 或 {"ip": "x.x.x.x", "as_number": 100}
                    # 兼容两种可能的AS号字段名称
                    self.connection.send_command_timing(
                        f"peer {neighbor['ip']} as-number {neighbor.get('as_number', neighbor.get('as', '0'))}"
                    )
                else:
                    # 简单格式: "x.x.x.x 100"
                    parts = neighbor.split()
                    if len(parts) >= 2:
                        self.connection.send_command_timing(
                            f"peer {parts[0]} as-number {parts[1]}"
                        )
            
            # 配置网络
            for network in networks:
                if "/" in network:
                    addr, mask_bits = network.split("/")
                    # 转换CIDR掩码为点分十进制
                    mask = self._cidr_to_mask(int(mask_bits))
                    self.connection.send_command_timing(f"network {addr} {mask}")
                else:
                    self.connection.send_command_timing(f"network {network}")
            
            # 退出BGP配置
            self.connection.send_command_timing("quit")
            
            # 保存配置
            self.connection.send_command_timing("return")
            save_output = self.connection.send_command_timing("save")
            if "Y/N" in save_output:
                self.connection.send_command_timing("y")
            
            self.config_status.emit(
                self.device_info['ip'], 
                True, 
                f"BGP配置成功: AS{as_number}"
            )
            return True
        except Exception as e:
            self.config_status.emit(
                self.device_info['ip'], 
                False, 
                f"BGP配置失败: {str(e)}"
            )
            return False
        finally:
            self.disconnect_device()
    
    def configure_vpn(self, vpn_name, rd, route_targets, interfaces=None):
        """配置VPN路由"""
        try:
            if not self.is_router:
                self.config_status.emit(
                    self.device_info['ip'], 
                    False, 
                    "只有路由器设备支持VPN配置"
                )
                return False
                
            if not self.connection and not self.connect_device():
                return False
            
            # 进入系统视图
            self.connection.send_command_timing("system-view")
            
            # 启用MPLS LDP
            self.connection.send_command_timing("mpls lsr-id 1.1.1.1")
            self.connection.send_command_timing("mpls")
            self.connection.send_command_timing("mpls ldp")
            self.connection.send_command_timing("quit")
            
            # 创建VPN实例
            self.connection.send_command_timing(f"ip vpn-instance {vpn_name}")
            
            # 配置RD值
            self.connection.send_command_timing(f"route-distinguisher {rd}")
            
            # 配置RT值
            for rt in route_targets:
                if isinstance(rt, dict):
                    # 格式: {"type": "import/export", "value": "100:1"}
                    self.connection.send_command_timing(
                        f"vpn-target {rt['value']} {rt['type']}"
                    )
                else:
                    # 简单格式: "100:1 export"
                    parts = rt.split()
                    if len(parts) >= 2:
                        self.connection.send_command_timing(
                            f"vpn-target {parts[0]} {parts[1]}"
                        )
                    else:
                        # 默认导入导出
                        self.connection.send_command_timing(f"vpn-target {rt} both")
            
            # 退出VPN实例配置
            self.connection.send_command_timing("quit")
            
            # 配置接口绑定VPN实例
            if interfaces:
                for interface in interfaces:
                    self.connection.send_command_timing(f"interface {interface}")
                    self.connection.send_command_timing(f"ip binding vpn-instance {vpn_name}")
                    self.connection.send_command_timing("quit")
            
            # 保存配置
            self.connection.send_command_timing("return")
            save_output = self.connection.send_command_timing("save")
            if "Y/N" in save_output:
                self.connection.send_command_timing("y")
            
            self.config_status.emit(
                self.device_info['ip'], 
                True, 
                f"VPN配置成功: {vpn_name}, RD: {rd}"
            )
            return True
        except Exception as e:
            self.config_status.emit(
                self.device_info['ip'], 
                False, 
                f"VPN配置失败: {str(e)}"
            )
            return False
        finally:
            self.disconnect_device()
    
    def _cidr_to_wildcard(self, cidr):
        """将CIDR掩码转换为反掩码"""
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        wildcard = ~mask & 0xffffffff
        return f"{(wildcard >> 24) & 0xff}.{(wildcard >> 16) & 0xff}.{(wildcard >> 8) & 0xff}.{wildcard & 0xff}"
    
    def _cidr_to_mask(self, cidr):
        """将CIDR掩码转换为点分十进制掩码"""
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"