import re
import sys
import time
import threading
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from PyQt5.QtCore import QObject, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
# 导入线程工厂
from core.business.thread_factory import ThreadFactory

# 华为设备操作类（使用Netmiko）
class HuaweiNetmikoOperator(QObject):
    status_signal = pyqtSignal(str, str, dict)  # 信号：设备IP, 状态, 详细信息
    progress_signal = pyqtSignal(str, int)      # 信号：设备IP, 进度百分比
    repair_result = pyqtSignal(str, bool)       # 信号：设备IP, 修复结果

    def __init__(self, ip, username="1", password="1", device_type="huawei_telnet"):
        """初始化操作类"""
        super().__init__()
        self.device_info = {
            'device_type': device_type,
            'ip': ip,
            'username': username,
            'password': password,
            'port': 23 if 'telnet' in device_type else 22,
            'secret': '',
            'session_timeout': 60,
            'timeout': 20,
            'global_delay_factor': 2,
        }
        self.connection = None
        self.max_attempts = 3
        self.connection_attempts = 0
        self.last_status_data = {}  # 用于缓存上次获取的状态数据
        self.last_status = "unknown"  # 初始状态为未知
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()

    def connect_device(self):
        """连接到设备，尝试不同的连接方法"""
        self.connection_attempts += 1
        try:
            print(f"NM: 尝试连接 {self.device_info['ip']} ({self.connection_attempts}/{self.max_attempts})")
            
            # 增加连接超时时间
            connection_info = self.device_info.copy()
            connection_info['session_timeout'] = 300  # 增加会话超时时间到300秒
            connection_info['timeout'] = 60  # 增加连接超时时间到60秒
            connection_info['global_delay_factor'] = 5  # 增加全局延迟因子，更加容忍网络延迟
            
            try:
                # 首先尝试Telnet连接
                self.connection = ConnectHandler(**connection_info)
                self.connection_attempts = 0  # 重置尝试计数
                print(f"NM: 连接成功 {self.device_info['ip']}")
                
                # 发送一个简单命令测试连接
                result = self.connection.send_command("display version", delay_factor=2, max_loops=200)
                if result and len(result.strip()) > 10:
                    print(f"NM: 设备 {self.device_info['ip']} 版本检查成功")
                    self.status_signal.emit(self.device_info['ip'], "connected", {})
                    return True
                else:
                    print(f"NM: 设备 {self.device_info['ip']} 版本检查返回内容不足")
                    self.connection.disconnect()
                    self.connection = None
                    # 将继续尝试SSH连接
            except (NetmikoTimeoutException, NetmikoAuthenticationException) as telnet_error:
                print(f"NM: Telnet连接失败 - {str(telnet_error)[:100]}")
                if self.connection:
                    try:
                        self.connection.disconnect()
                    except:
                        pass
                    self.connection = None
            
            # 如果Telnet失败，尝试SSH连接
            try:
                print(f"NM: 尝试SSH连接 {self.device_info['ip']}")
                # 尝试SSH连接
                ssh_device_info = self.device_info.copy()
                ssh_device_info['device_type'] = self.device_info['device_type'].replace('telnet', 'ssh')
                if 'ssh' not in ssh_device_info['device_type']:
                    ssh_device_info['device_type'] = 'huawei'  # 默认使用华为SSH
                
                ssh_device_info['session_timeout'] = 300  # 增加会话超时时间到300秒
                ssh_device_info['timeout'] = 60  # 增加连接超时时间到60秒
                ssh_device_info['global_delay_factor'] = 5  # 增加全局延迟因子
                
                self.connection = ConnectHandler(**ssh_device_info)
                self.connection_attempts = 0  # 重置尝试计数
                print(f"NM: SSH连接成功 {self.device_info['ip']}")
                
                # 发送一个简单命令测试连接
                result = self.connection.send_command("display version", delay_factor=2, max_loops=200)
                if result and len(result.strip()) > 10:
                    print(f"NM: 设备 {self.device_info['ip']} SSH版本检查成功")
                    self.status_signal.emit(self.device_info['ip'], "connected", {})
                    return True
                else:
                    print(f"NM: 设备 {self.device_info['ip']} SSH版本检查返回内容不足")
                    # 如果命令返回内容不足，认为连接不完全
                    if self.connection:
                        self.connection.disconnect()
                        self.connection = None
                    return False
            except (NetmikoTimeoutException, NetmikoAuthenticationException) as ssh_error:
                print(f"NM: SSH连接失败 - {str(ssh_error)[:100]}")
                
                # 检查是否需要继续尝试连接
                if self.connection_attempts >= self.max_attempts:
                    self.connection_attempts = 0  # 重置尝试计数
                    
                    # 检查是否有缓存数据
                    if hasattr(self, 'last_status_data') and self.last_status_data:
                        # 检查缓存是否过期
                        cached_timestamp = self.last_status_data.get('timestamp', 0)
                        current_time = time.time()
                        cache_age = current_time - cached_timestamp
                        
                        if cache_age < 300:  # 5分钟内的缓存数据仍然有效
                            print(f"NM: 使用缓存数据 ({int(cache_age)}秒)")
                            cached_data = self.last_status_data.copy()
                            self.status_signal.emit(self.device_info['ip'], "cached", cached_data)
                    
                    self.status_signal.emit(self.device_info['ip'], "disconnected", {"error": str(ssh_error)})
                    return False
                else:
                    print(f"NM: 连接失败，将重试")
                    return False
        except Exception as e:
            print(f"NM: 连接错误 {self.device_info['ip']} - {str(e)[:100]}")
            import traceback
            print(f"NM: 连接错误详情: {traceback.format_exc()[:300]}")
            
            if self.connection_attempts >= self.max_attempts:
                self.connection_attempts = 0  # 重置尝试计数
                self.status_signal.emit(self.device_info['ip'], "error", {"error": str(e)})
                return False
            return False

    def get_device_status(self):
        """获取设备状态（CPU、内存、接口）"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._get_device_status_thread,
            name=f"DeviceStatus-{self.device_info['ip']}",
            module="网络监控模块"
        )
        return True
        
    def _get_device_status_thread(self):
        """线程中获取设备状态（CPU、内存、接口）"""
        try:
            print(f"NM: [TEST] 开始获取设备 {self.device_info['ip']} 的状态")
            
            # 首先检查是否已连接，如果没有则尝试连接
            is_connected = self.is_connected()
            if not is_connected:
                print(f"NM: [TEST] 设备 {self.device_info['ip']} 未连接，尝试连接")
                is_connected = self.connect_device()
                if not is_connected:
                    print(f"NM: [TEST] 设备 {self.device_info['ip']} 连接失败")
                    
                    # 如果有缓存数据且在有效期内，尝试使用缓存数据
                    if hasattr(self, 'last_status_data') and self.last_status_data:
                        current_time = time.time()
                        timestamp = self.last_status_data.get('timestamp', 0)
                        cache_age = current_time - timestamp if timestamp > 0 else 999999
                        
                        if cache_age < 300:  # 5分钟内的缓存数据仍然有效
                            print(f"NM: [TEST] 由于无法连接使用设备 {self.device_info['ip']} 的缓存数据")
                            cached_data = self.last_status_data.copy()
                            self.status_signal.emit(self.device_info['ip'], "cached", cached_data)
                            return True
                    
                    # 发送断开连接状态
                    self.status_signal.emit(self.device_info['ip'], "disconnected", {})
                    return False

            # 获取CPU使用率
            print(f"NM: [TEST] 开始获取设备 {self.device_info['ip']} 的CPU使用率")
            cpu_usage = self._get_cpu_usage()
            print(f"NM: [TEST] 设备 {self.device_info['ip']} CPU使用率: {cpu_usage}%")
            
            # 获取内存使用率  
            print(f"NM: [TEST] 开始获取设备 {self.device_info['ip']} 的内存使用率")
            memory_usage = self._get_memory_usage()
            print(f"NM: [TEST] 设备 {self.device_info['ip']} 内存使用率: {memory_usage}%")
            
            # 获取接口状态
            print(f"NM: [TEST] 开始获取设备 {self.device_info['ip']} 的接口状态")  
            interfaces = self._get_interfaces_status()
            print(f"NM: [TEST] 设备 {self.device_info['ip']} 接口数量: {len(interfaces)}")
            
            # 保存状态数据
            status_data = {
                'cpu': cpu_usage,
                'mem': memory_usage,
                'interfaces': interfaces,
                'timestamp': time.time()
            }
            
            # 判断设备状态
            status = "connected"
            
            # 如果CPU或内存使用率过高，则设备状态为警告
            if cpu_usage > 80 or memory_usage > 80:
                status = "warning"
                print(f"NM: [TEST] 设备 {self.device_info['ip']} 资源使用率过高")
            
            # 检查接口状态，如果有错误接口，状态为warning
            error_interfaces = [i for i in interfaces if i.get('status') == 'down' or i.get('errors', 0) > 0]
            if len(error_interfaces) > 0:
                status = "warning"
                print(f"NM: [TEST] 设备 {self.device_info['ip']} 有 {len(error_interfaces)} 个问题接口")
            
            # 保存最后状态数据
            self.last_status_data = status_data.copy()
            self.last_status = status
            
            # 发送设备状态信号
            print(f"NM: [TEST] 发送设备 {self.device_info['ip']} 状态信号: {status}")
            self.status_signal.emit(self.device_info['ip'], status, status_data)
            
            return True
        except Exception as e:
            import traceback
            print(f"NM: [TEST] 获取设备 {self.device_info['ip']} 状态异常: {str(e)}")
            print(traceback.format_exc())
            
            # 如果有缓存数据且在有效期内，尝试使用缓存数据
            if hasattr(self, 'last_status_data') and self.last_status_data:
                current_time = time.time()
                timestamp = self.last_status_data.get('timestamp', 0)
                cache_age = current_time - timestamp if timestamp > 0 else 999999
                
                if cache_age < 300:  # 5分钟内的缓存数据仍然有效
                    print(f"NM: [TEST] 由于异常使用设备 {self.device_info['ip']} 的缓存数据")
                    cached_data = self.last_status_data.copy()
                    self.status_signal.emit(self.device_info['ip'], "cached", cached_data)
                    return True
            
            # 发送错误状态
            self.status_signal.emit(self.device_info['ip'], "error", {"error": str(e)})
            return False

    def reboot_device(self):
        """重启设备"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._reboot_device_thread,
            name=f"DeviceReboot-{self.device_info['ip']}",
            module="网络监控模块"
        )
        return True
        
    def _reboot_device_thread(self):
        """在线程中执行设备重启"""
        success = False
        try:
            if self.connect_device():
                # 发送reboot命令并处理两次确认
                output = self.connection.send_command_timing(
                    'reboot',
                    strip_prompt=False,
                    strip_command=False
                )
                
                # 处理第一次确认保存配置
                if 'Continue?[Y/N]' in output:
                    output += self.connection.send_command_timing(
                        'y',
                        strip_prompt=False,
                        strip_command=False
                    )
                    
                # 处理第二次确认重启
                if 'Continue?[Y/N]' in output:
                    output += self.connection.send_command_timing(
                        'y',
                        strip_prompt=False,
                        strip_command=False
                    )
                    
                success = 'System will reboot' in output
        except Exception as e:
            print(f"重启失败: {str(e)}")
        finally:
            self.repair_result.emit(self.device_info['ip'], success)
            if self.connection:
                self.connection.disconnect()
                
    def repair_interface(self, interface_name):
        """修复接口状态"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._repair_interface_thread,
            args=(interface_name,),
            name=f"InterfaceRepair-{self.device_info['ip']}-{interface_name}",
            module="网络监控模块"
        )
        return True
        
    def _repair_interface_thread(self, interface_name):
        """在线程中执行接口修复"""
        success = False
        try:
            if self.connect_device():
                # 进入系统视图
                system_output = self.connection.send_command_timing("system-view")
                if "Error" in system_output or "错误" in system_output:
                    print(f"进入系统视图失败: {system_output}")
                    raise Exception(f"进入系统视图失败: {system_output}")
                
                # 进入接口配置模式
                interface_output = self.connection.send_command_timing(f"interface {interface_name}")
                if "Error" in interface_output or "错误" in interface_output:
                    print(f"进入接口 {interface_name} 配置模式失败: {interface_output}")
                    raise Exception(f"进入接口配置模式失败: {interface_output}")
                
                # 先关闭接口
                shutdown_output = self.connection.send_command_timing("shutdown")
                if "Error" in shutdown_output or "错误" in shutdown_output:
                    print(f"关闭接口失败: {shutdown_output}")
                    raise Exception(f"关闭接口失败: {shutdown_output}")
                time.sleep(2)  # 等待接口状态变化
                
                # 再打开接口
                undo_output = self.connection.send_command_timing("undo shutdown")
                if "Error" in undo_output or "错误" in undo_output:
                    print(f"打开接口失败: {undo_output}")
                    raise Exception(f"打开接口失败: {undo_output}")
                time.sleep(2)  # 等待接口状态变化
                
                # 退出接口配置模式
                self.connection.send_command_timing("quit")
                
                # 退出系统视图
                self.connection.send_command_timing("quit")
                
                # 保存配置
                save_output = self.connection.send_command_timing("save")
                if 'Y/N' in save_output:
                    save_output += self.connection.send_command_timing("y")
                    if "successfully" in save_output or "成功" in save_output:
                        success = True
                        print(f"接口 {interface_name} 修复成功")
                    else:
                        print(f"保存配置失败: {save_output}")
        except Exception as e:
            print(f"修复接口 {interface_name} 失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.repair_result.emit(self.device_info['ip'], success)
            if self.connection:
                self.connection.disconnect()

    def _get_cpu_usage(self):
        """获取CPU使用率"""
        if not self.connection:
            print(f"NM: 获取CPU使用率失败 - 没有连接")
            return 0
            
        # 直接使用正确的命令获取CPU使用率
        print(f"NM: 设备 {self.device_info['ip']} 开始获取CPU使用率")
        try:
            output = self.connection.send_command_timing(
                "display cpu-usage", 
                delay_factor=2.0,  # 增加延迟因子
                max_loops=300,     # 增加等待循环次数
                strip_prompt=False
            )
            
            print(f"NM: 设备 {self.device_info['ip']} 原始CPU使用率输出: {output[:50]}...")
            
            # 使用更精确的匹配模式
            cpu_patterns = [
                r'CPU Usage\s*:\s*(\d+)%',                         # 当前使用率
                r'CPU utilization for five seconds:\s*(\d+)%',     # 5秒使用率
                r'Five seconds:\s*(\d+)%',                         # 5秒使用率
                r'Current CPU usage is\s*(\d+)%',                  # 当前使用率
                r'CPU usage:\s*(\d+)%',                            # 当前使用率
                r'CPU \d+\s+usage ratio: (\d+)%',                  # CPU x使用率
                r'(\d+)%',                                         # 任何百分比
            ]
            
            # 尝试匹配CPU值
            for pattern in cpu_patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    try:
                        cpu_value = int(match.group(1))
                        if 0 <= cpu_value <= 100:  # 确保值在合理范围内
                            print(f"NM: 设备 {self.device_info['ip']} CPU使用率: {cpu_value}%")
                            return cpu_value
                    except (ValueError, IndexError):
                        continue
            
            # 如果没有找到匹配，返回默认值
            return 50  # 默认返回中等负载
            
        except Exception as e:
            print(f"NM: 获取CPU使用率异常: {str(e)}")
            return 50  # 出错时返回中等值表示未知
        
    def _get_memory_usage(self):
        """获取内存使用率"""
        if not self.connection:
            print(f"NM: 获取内存使用率失败 - 没有连接")  
            return 0
            
        # 直接使用正确的命令获取内存使用率
        print(f"NM: 设备 {self.device_info['ip']} 开始获取内存使用率")
        try:
            output = self.connection.send_command_timing(
                "display memory-usage",
                delay_factor=2.0,
                max_loops=300,
                strip_prompt=False
            )
            
            print(f"NM: 设备 {self.device_info['ip']} 原始内存使用率输出: {output[:50]}...")
            
            # 使用更精确的匹配模式
            mem_patterns = [
                r'Memory Using Percentage Is:\s*(\d+)%',     # 华为常用格式
                r'Memory utilization\s*:\s*(\d+)%',          # 另一种格式
                r'Memory usage\s*:\s*(\d+)%',                # 通用格式
                r'Memory usage is\s*(\d+)%',                 # 通用格式
                r'Used\s*:\s*(\d+)%',                        # 精简格式
                r'(\d+)%',                                   # 任何百分比
            ]
            
            for pattern in mem_patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    try:
                        mem_value = int(match.group(1))
                        if 0 <= mem_value <= 100:  # 确保值在合理范围内
                            print(f"NM: 设备 {self.device_info['ip']} 内存使用率: {mem_value}%")
                            return mem_value
                    except (ValueError, IndexError):
                        continue
            
            # 如果没有找到匹配，返回默认值
            return 60  # 默认返回适中内存使用率
            
        except Exception as e:
            print(f"NM: 获取内存使用率异常: {str(e)}")
            return 60  # 出错时返回中等值表示未知
        
    def _get_interfaces_status(self):
        """获取接口状态"""
        if not self.connection:
            print(f"NM: 获取接口状态失败 - 没有连接")
            return []
            
        print(f"NM: 设备 {self.device_info['ip']} 开始获取接口状态")
        try:
            # 尝试不同的命令获取接口状态
            commands = [
                "display interface brief",
                "display interface brief | include Eth|GE|XGE",
                "display interface brief | include up|down",
                "display interface",
                "display port status"
            ]
            
            output = ""
            for cmd in commands:
                try:
                    print(f"NM: 设备 {self.device_info['ip']} 尝试命令: {cmd}")
                    cmd_output = self.connection.send_command_timing(
                        cmd, 
                        delay_factor=2.0, 
                        max_loops=300,
                        strip_prompt=False
                    )
                    
                    if cmd_output and len(cmd_output.strip()) > 10:
                        # 检查输出是否包含有意义的内容
                        if (("Interface" in cmd_output or "Port" in cmd_output) and 
                            ("up" in cmd_output.lower() or "down" in cmd_output.lower())):
                            print(f"NM: 设备 {self.device_info['ip']} 获取到接口信息: {len(cmd_output.splitlines())} 行")
                            output = cmd_output
                            break
                except Exception as e:
                    print(f"NM: 设备 {self.device_info['ip']} 命令 {cmd} 执行失败: {str(e)[:50]}")
                    continue
            
            # 如果所有命令都无法获取有意义的输出，返回空接口列表
            if not output:
                print(f"NM: 设备 {self.device_info['ip']} 无法获取接口状态")
                return []
            
            # 解析接口状态
            interfaces = []
            for line in output.splitlines():
                line = line.strip()
                # 跳过表头和空行
                if not line or "----" in line or "Interface" in line or "Port" in line:
                    continue
                
                # 尝试解析行数据
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                interface_name = parts[0]
                
                # 跳过无用接口
                if any(skip in interface_name.lower() for skip in ["null", "inloop", "outloop", "meth"]):
                    continue
                
                # 解析接口状态
                status = "down"
                admin_status = "up"
                
                # 检查接口是否up
                if len(parts) >= 2:
                    phys_status = parts[1].lower()
                    if "up" in phys_status:
                        status = "up"
                    # 检查是否为管理性关闭
                    if "*down" in phys_status or "admin" in phys_status:
                        admin_status = "down"
                
                # 接口错误计数 (默认为0)
                errors = 0
                
                # 添加接口信息
                interfaces.append({
                    'name': interface_name,
                    'status': status,
                    'admin_status': admin_status,
                    'errors': errors
                })
            
            # 如果没有解析到任何接口，尝试简单的匹配
            if not interfaces:
                print(f"NM: 设备 {self.device_info['ip']} 尝试简单接口解析")
                # 简单匹配任何包含interface/port和up/down的行
                interface_pattern = r'([A-Za-z0-9\/\-\.]+)\s+(up|down|UP|DOWN)'
                matches = re.findall(interface_pattern, output)
                for match in matches:
                    if len(match) >= 2:
                        interface_name = match[0]
                        status = match[1].lower()
                        interfaces.append({
                            'name': interface_name,
                            'status': status,
                            'admin_status': 'up',
                            'errors': 0
                        })
            
            up_count = sum(1 for i in interfaces if i['status'] == 'up')
            print(f"NM: 设备 {self.device_info['ip']} 成功获取 {len(interfaces)} 个接口, {up_count} 个UP")
            return interfaces
        except Exception as e:
            print(f"NM: 设备 {self.device_info['ip']} 获取接口状态异常: {str(e)}")
            return []

    def is_connected(self):
        """检查设备连接状态"""
        if not self.connection:
            return False
        try:
            # 尝试执行一个简单命令验证连接是否还活跃
            test_cmd = "display version"
            try:
                output = self.connection.send_command_timing(
                    test_cmd,
                    delay_factor=1.0,
                    max_loops=100,
                    strip_prompt=False
                )
                if "Error" in output or len(output.strip()) < 5:
                    print(f"NM: 连接测试失败 - {output}")
                    return False
                else:
                    print(f"NM: 连接测试成功")
                    return True
            except Exception as e:
                print(f"NM: 连接测试异常 - {e}")
                return False
        except Exception:
            return False
            
    def get_device_version(self):
        """获取设备版本信息"""
        try:
            if not self.connection:
                return None
                
            output = self.connection.send_command_timing(
                "display version", 
                delay_factor=1.0,
                max_loops=100,
                strip_prompt=False
            )
            
            if output and len(output.strip()) > 10:
                return output
            return None
        except Exception as e:
            print(f"获取版本信息错误: {e}")
            return None

    def _send_status_signal(self, status, data=None):
        """发送状态信号
        
        参数:
            status (str): 状态，如connected, disconnected, error等
            data (dict): 状态详细数据
        """
        if data is None:
            data = {}
            
        try:
            print(f"NM: 发送设备 {self.device_info['ip']} 状态信号: {status}")
            # 保存最后状态
            self.last_status = status
            # 发送信号
            self.status_signal.emit(self.device_info['ip'], status, data)
            return True
        except Exception as e:
            print(f"NM: 发送状态信号失败: {e}")
            return False
            
    def force_refresh(self):
        """强制刷新设备状态，用于测试是否使用缓存数据"""
        print(f"NM: [TEST] 强制刷新设备 {self.device_info['ip']} 状态")
        
        # 清除缓存状态数据
        if hasattr(self, 'last_status_data'):
            print(f"NM: [TEST] 清除设备 {self.device_info['ip']} 的缓存状态数据")
            self.last_status_data = {}
        
        # 如果连接存在，尝试断开重连
        if self.connection:
            try:
                print(f"NM: [TEST] 断开设备 {self.device_info['ip']} 的连接")
                self.connection.disconnect()
            except Exception as e:
                print(f"NM: [TEST] 断开连接时出错: {e}")
            finally:
                self.connection = None
        
        # 重置连接尝试计数
        self.connection_attempts = 0
        
        # 获取最新状态
        return self.get_device_status()

# 批量设备监控类
class BatchDeviceMonitor(QObject):
    all_devices_checked = pyqtSignal()
    
    def __init__(self, devices):
        super().__init__()
        self.devices = devices
        self.operators = {}
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        
    def start_monitoring(self):
        """开始监控所有设备"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._monitor_all_devices,
            name="BatchDeviceMonitor",
            module="网络监控模块"
        )
        return True
        
    def _monitor_all_devices(self):
        """在线程中执行批量设备监控"""
        for device in self.devices:
            ip = device.get('ip')
            username = device.get('username', '1')
            password = device.get('password', '1')
            
            if ip not in self.operators:
                operator = HuaweiNetmikoOperator(ip, username, password)
                self.operators[ip] = operator
            
            # 获取设备状态
            self.operators[ip].get_device_status()
            
            # 短暂延时，避免同时发起太多连接
            time.sleep(1)
        
        # 发送所有设备检查完成信号
        self.all_devices_checked.emit()