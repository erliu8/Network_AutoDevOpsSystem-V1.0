import re
import time
from PyQt5.QtCore import QObject, pyqtSignal
# 导入线程工厂
from core.business.thread_factory import ThreadFactory
import threading

class ENSPMonitor(QObject):
    # 定义信号
    traffic_data = pyqtSignal(dict)  # 流量数据信号
    data_updated = pyqtSignal(dict)  # 与MonitorService兼容的数据更新信号
    status_signal = pyqtSignal(str, str)  # 状态信号(设备IP, 状态)
    
    def __init__(self, ip, username, password):
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password
        self.connection = None
        self.monitoring = False
        self.connected = False
        self.max_retries = 3  # 最大重试次数
        self.retry_interval = 5  # 重试间隔（秒）
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
    
    def connect_device(self):
        """连接设备"""
        try:
            # 改用netmiko的Telnet连接
            from netmiko import ConnectHandler
            
            device = {
                'device_type': 'huawei_telnet',  # 使用华为telnet类型
                'ip': self.ip,
                'username': self.username,
                'password': self.password,
                'port': 23,  # telnet端口
                'timeout': 15,
            }
            
            print(f"正在连接设备 {self.ip}...")
            self.connection = ConnectHandler(**device)
            
            print(f"成功连接到设备 {self.ip}")
            self.status_signal.emit(self.ip, "connected")
            self.connected = True
            return True
        except Exception as e:
            import traceback
            print(f"连接设备 {self.ip} 失败: {str(e)}")
            print(traceback.format_exc())
            self.status_signal.emit(self.ip, f"disconnected: {str(e)}")
            self.connected = False
            return False
    
    def start_monitoring(self):
        """开始监控流量"""
        if self.monitoring:
            print("监控已经在运行中")
            return False
        
        # 确保已连接
        if not self.connected:
            print("设备未连接，请先连接设备")
            return False
            
        self.monitoring = True
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._monitor_thread,
            name=f"TrafficMonitor-{self.ip}",
            module="流量监控模块"
        )
        print(f"已启动对设备 {self.ip} 的流量监控")
        return True
    
    def _monitor_thread(self):
        """在线程中执行流量监控"""
        thread_id = threading.get_ident()
        print(f"ENSPMonitor: 流量监控线程已启动 (设备: {self.ip}, 线程ID: {thread_id})")
        
        connection_retry_count = 0
        max_connection_retries = 3
        empty_data_count = 0
        
        try:
            # 获取接口列表
            interfaces = self._get_interfaces()
            if not interfaces:
                print(f"ENSPMonitor: 未获取到设备 {self.ip} 的接口列表")
                self.monitoring = False
                self.status_signal.emit(self.ip, "stopped")
                return
            
            print(f"ENSPMonitor: 设备 {self.ip} 接口列表: {interfaces}")
            
            # 循环监控流量
            while self.monitoring and self.connected:
                try:
                    # 首先检查连接是否正常
                    if not self._check_connection():
                        connection_retry_count += 1
                        print(f"ENSPMonitor: 设备 {self.ip} 连接检查失败 (尝试 {connection_retry_count}/{max_connection_retries})")
                        
                        if connection_retry_count >= max_connection_retries:
                            print(f"ENSPMonitor: 设备 {self.ip} 连接已断开，停止监控")
                            break
                        
                        # 暂停一下再重试
                        time.sleep(2)
                        continue
                    
                    # 连接正常，重置重试计数
                    connection_retry_count = 0
                    
                    traffic_info = {}
                    
                    for interface in interfaces:
                        # 如果监控已停止，提前退出
                        if not self.monitoring:
                            break
                            
                        # 获取接口流量
                        stats = self._get_interface_traffic(interface)
                        if stats:
                            # 将流量数据格式化为字节每秒
                            traffic_info[interface] = {
                                "input": stats.get('input_rate', 0) // 8,  # bits/sec 转换为 bytes/sec
                                "output": stats.get('output_rate', 0) // 8  # bits/sec 转换为 bytes/sec
                            }
                    
                    # 如果监控已停止，不发送数据
                    if not self.monitoring:
                        break
                        
                    if traffic_info:
                        print(f"ENSPMonitor: 获取到 {self.ip} 的流量数据: {len(traffic_info)} 个接口")
                        # 发送流量数据信号
                        if self.monitoring:  # 再次检查，避免在发送信号前监控已停止
                            self.traffic_data.emit(traffic_info)
                            self.data_updated.emit(traffic_info)
                        # 重置空数据计数
                        empty_data_count = 0
                    else:
                        empty_data_count += 1
                        print(f"ENSPMonitor: 未获取到 {self.ip} 的流量数据 (连续 {empty_data_count} 次)")
                        
                        # 如果连续多次未获取到数据，可能需要重新获取接口列表
                        if empty_data_count >= 3:
                            print(f"ENSPMonitor: 尝试重新获取接口列表")
                            new_interfaces = self._get_interfaces()
                            if new_interfaces:
                                interfaces = new_interfaces
                                empty_data_count = 0
                    
                    # 等待一段时间再次获取（使用更小的间隔检查停止标志）
                    for _ in range(5):  # 5秒，每秒检查一次
                        if not self.monitoring:
                            break
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"ENSPMonitor: 获取流量数据时出错: {str(e)}")
                    # 如果出错但监控仍在运行，等待后继续
                    if self.monitoring:
                        time.sleep(2)
                
        except Exception as e:
            import traceback
            print(f"ENSPMonitor: 流量监控线程异常: {str(e)}")
            print(traceback.format_exc())
        
        finally:
            # 无论如何都确保资源被释放
            print(f"ENSPMonitor: 流量监控线程退出 (设备: {self.ip}, 线程ID: {thread_id})")
            self.monitoring = False
            
            # 断开连接前发送最终状态信号
            self.status_signal.emit(self.ip, "stopped")
            
            # 清理连接资源
            self.connected = False
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                finally:
                    self.connection = None
    
    def _check_connection(self):
        """检查连接是否正常"""
        try:
            if not self.connection:
                return False
                
            # 尝试执行一个简单的命令来测试连接
            result = self.connection.send_command("display version", expect_string=r"[\r\n]", delay_factor=2)
            
            if result and len(result) > 0:
                # 连接正常
                if not self.connected:
                    print(f"设备 {self.ip} 连接已恢复")
                    self.connected = True
                    self.status_signal.emit(self.ip, "connected")
                return True
            else:
                # 连接异常
                if self.connected:
                    print(f"设备 {self.ip} 连接已断开")
                    self.connected = False
                    self.status_signal.emit(self.ip, "disconnected")
                return False
        except Exception as e:
            # 连接异常
            print(f"检查连接异常: {str(e)}")
            if self.connected:
                self.connected = False
                self.status_signal.emit(self.ip, "disconnected")
            return False
    
    def stop_monitoring(self):
        """停止监控"""
        print(f"ENSPMonitor: 停止设备 {self.ip} 的监控")
        
        # 设置停止标志
        old_monitoring = self.monitoring
        self.monitoring = False
        
        # 等待线程退出（最多等待1秒）
        if old_monitoring:
            time.sleep(0.5)  # 给线程一些时间来退出
            
        # 强制断开连接
        self.connected = False
        if self.connection:
            try:
                print(f"ENSPMonitor: 断开设备 {self.ip} 的连接")
                self.connection.disconnect()
            except:
                pass
            finally:
                self.connection = None
        
        # 发送停止信号
        self.status_signal.emit(self.ip, "stopped")
        print(f"ENSPMonitor: 设备 {self.ip} 的监控已停止")
    
    def _get_interfaces(self):
        """获取设备接口列表"""
        interfaces = []
        try:
            # 使用netmiko执行命令
            output = self.connection.send_command("display interface brief")
            
            # 解析接口列表
            for line in output.split('\n'):
                if 'GigabitEthernet' in line:
                    parts = line.split()
                    if len(parts) > 0:
                        interfaces.append(parts[0])
            
            # 不再限制接口数量，返回所有找到的接口
            print(f"设备 {self.ip} 发现 {len(interfaces)} 个GigabitEthernet接口")
            return interfaces
            
        except Exception as e:
            import traceback
            print(f"获取接口列表异常: {str(e)}")
            print(traceback.format_exc())
            self.status_signal.emit(self.ip, f"error: {str(e)}")
            return []
    
    def _get_interface_traffic(self, interface):
        """获取接口流量统计"""
        try:
            # 使用netmiko执行命令，增加超时并设置明确的预期匹配
            output = self.connection.send_command(
                f"display interface {interface}", 
                expect_string=r"#|>",  # 使用更明确的命令提示符匹配
                delay_factor=3,  # 增加延迟因子
                max_loops=500  # 增加最大循环次数
            )
            
            # 解析流量数据
            stats = {}
            
            # 提取输入速率
            input_pattern = r"Input.+?(\d+)\s+bits/sec"
            match = re.search(input_pattern, output, re.DOTALL)
            if match:
                stats['input_rate'] = int(match.group(1))
            else:
                stats['input_rate'] = 0  # 提供默认值
            
            # 提取输出速率
            output_pattern = r"Output.+?(\d+)\s+bits/sec"
            match = re.search(output_pattern, output, re.DOTALL)
            if match:
                stats['output_rate'] = int(match.group(1))
            else:
                stats['output_rate'] = 0  # 提供默认值
            
            # 提取输入包数
            in_packets_pattern = r"Input.+?(\d+)\s+packets"
            match = re.search(in_packets_pattern, output, re.DOTALL)
            if match:
                stats['in_packets'] = int(match.group(1))
            
            # 提取输出包数
            out_packets_pattern = r"Output.+?(\d+)\s+packets"
            match = re.search(out_packets_pattern, output, re.DOTALL)
            if match:
                stats['out_packets'] = int(match.group(1))
            
            return stats
        except Exception as e:
            import traceback
            print(f"获取接口 {interface} 流量统计异常: {str(e)}")
            print(traceback.format_exc())
            
            # 如果监控仍在运行，仅报告错误，但不停止监控
            # 避免单个接口问题导致整个监控停止
            if self.monitoring:
                # 发送警告而非错误状态，允许监控继续
                self.status_signal.emit(self.ip, f"warning: {interface} {str(e)}")
            
            # 返回默认数据而不是None，确保监控可以继续
            return {'input_rate': 0, 'output_rate': 0, 'in_packets': 0, 'out_packets': 0}