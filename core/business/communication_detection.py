# communication_detection.py
import sys
import os
import subprocess
import platform
from pathlib import Path
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.services.device_service import DeviceService

class CommunicationDetector(QObject):
    
    # 定义信号
    detection_result = pyqtSignal(dict)  # 检测结果信号
    
    def __init__(self):
        super().__init__()
        self.device_data = None
        self.connection_status = {}  # 存储连接状态
        self.running = False
        self.device_name_mapping = {
            # 地域1设备
            "地域1出口路由器": "地域1出口路由器",
            "地域1核心交换机": "地域1核心交换机",
            "地域1汇聚交换机A": "地域1汇聚交换机A",  # 修正名称
            "地域1汇聚交换机B": "地域1汇聚交换机B",  # 修正名称
            "接入交换机A1": "地域1接入交换机1(企业A)",
            "接入交换机A2": "地域1接入交换机2(企业A)",
            "接入交换机B1": "地域1接入交换机1(企业B)",
            "接入交换机B2": "地域1接入交换机2(企业B)",
            
            # 地域2设备
            "地域2出口路由器": "地域2出口路由器",
            "地域2核心交换机A": "地域2核心交换机(企业A)",
            "地域2核心交换机B": "地域2核心交换机(企业B)",
            "接入交换机A3": "地域2接入交换机1(企业A)",
            "接入交换机A4": "地域2接入交换机2(企业A)",
            "接入交换机B3": "地域2接入交换机1(企业B)",
            "接入交换机B4": "地域2接入交换机2(企业B)",
        }
    
    def start_detection(self):
        """开始检测网络连通性"""
        if self.running:
            return
            
        self.running = True
        # 在新线程中执行检测
        threading.Thread(target=self._detection_thread, daemon=True).start()
        print("网络连通性检测已启动")
        
    def stop_detection(self):
        """停止检测"""
        self.running = False
        print("网络连通性检测已停止")
    
    def _detection_thread(self):
        """检测线程"""
        retry_count = 0
        max_retries = 3
        
        while self.running:
            try:
                # 获取最新的设备数据
                self.device_data = DeviceService.get_device_data_dict()
                
                if not self.device_data:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print("错误: 多次尝试获取设备数据失败，等待下一轮检测")
                        threading.Event().wait(30)  # 等待30秒后重试
                        retry_count = 0
                        continue
                    print(f"警告: 未获取到设备数据，正在重试 ({retry_count}/{max_retries})")
                    threading.Event().wait(5)  # 等待5秒后重试
                    continue
                
                retry_count = 0  # 重置重试计数
                
                # 检测企业A内部连通性
                self._check_enterprise_connectivity("企业A")
                
                # 检测企业B内部连通性
                self._check_enterprise_connectivity("企业B")
                
                # 发送检测结果
                self.detection_result.emit(self.connection_status)
                print(f"已更新连通性状态: {len(self.connection_status)}个连接")
                
                # 等待一段时间再次检测
                for _ in range(30):  # 30秒检测间隔
                    if not self.running:
                        break
                    threading.Event().wait(1)
                    
            except Exception as e:
                print(f"网络连通性检测错误: {str(e)}")
                import traceback
                traceback.print_exc()
                # 出错后等待一段时间再重试
                threading.Event().wait(5)
    
    def _use_mock_data(self):
        """从设备服务获取真实数据"""
        try:
            # 尝试从设备服务获取数据
            self.device_data = DeviceService.get_device_data_dict()
            if not self.device_data:
                print("错误: 无法从设备服务获取数据")
                return
                
            print(f"成功获取设备数据: {len(self.device_data)}个设备")
            
        except Exception as e:
            print(f"获取设备数据错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _check_enterprise_connectivity(self, enterprise):
        """检测指定企业内部设备的连通性"""
        try:
            # 检查地域1接入交换机与汇聚交换机的连通性
            self._check_connection(
                f"地域1接入交换机1({enterprise})", 
                f"地域1汇聚交换机{enterprise[-1]}", 
                f"area1_access_a1_converge_{enterprise.lower()[-1]}",
                enterprise
            )
            
            self._check_connection(
                f"地域1接入交换机2({enterprise})", 
                f"地域1汇聚交换机{enterprise[-1]}", 
                f"area1_access_a2_converge_{enterprise.lower()[-1]}",
                enterprise
            )
            
            # 检查地域1汇聚交换机与核心交换机的连通性
            self._check_connection(
                f"地域1汇聚交换机{enterprise[-1]}", 
                "地域1核心交换机",
                f"area1_converge_core_{enterprise.lower()[-1]}",
                enterprise
            )
            
            # 检查地域1核心交换机与出口路由器的连通性
            self._check_connection(
                "地域1核心交换机", 
                "地域1出口路由器",
                f"area1_core_router_{enterprise.lower()[-1]}",
                enterprise
            )
            
            # 检查地域2接入交换机与核心交换机的连通性
            for i in range(1, 3):
                self._check_connection(
                    f"地域2接入交换机{i}({enterprise})", 
                    f"地域2核心交换机({enterprise})",
                    f"area2_core_{enterprise.lower()[-1]}",
                    enterprise
                )
            
            # 检查地域2核心交换机与出口路由器的连通性
            self._check_connection(
                f"地域2核心交换机({enterprise})", 
                "地域2出口路由器",
                f"area2_core_router_{enterprise.lower()[-1]}",
                enterprise
            )
            
            # 检查地域1出口路由器与地域2出口路由器的连通性（通过运营商网络）
            self._check_connection(
                "地域1出口路由器", 
                "地域2出口路由器",
                f"area1_router_area2_router_{enterprise.lower()[-1]}",
                enterprise
            )
                    
        except Exception as e:
            print(f"检测企业{enterprise}连通性错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _check_connection(self, source_device, target_device, connection_key, enterprise):
        """检查两个设备之间的连通性"""
        try:
            # 获取设备IP
            source_ip = None
            target_ip = None
            
            # 从设备数据中获取IP
            if source_device in self.device_data:
                source_ip = self.device_data[source_device].get(enterprise)
                if not source_ip:
                    print(f"警告: {source_device} 没有企业{enterprise}的IP配置")
            else:
                print(f"错误: 找不到设备 {source_device}")
            
            if target_device in self.device_data:
                target_ip = self.device_data[target_device].get(enterprise)
                if not target_ip:
                    print(f"警告: {target_device} 没有企业{enterprise}的IP配置")
            else:
                print(f"错误: 找不到设备 {target_device}")
            
            # 如果两个设备都有IP，则进行连通性检测
            if source_ip and target_ip:
                print(f"正在检测连接: {source_device}({source_ip}) -> {target_device}({target_ip})")
                status = self._ping_device(target_ip)
                self.connection_status[connection_key] = 1 if status else 0
                print(f"连接 {source_device} -> {target_device} ({enterprise}): {'成功' if status else '失败'}")
            else:
                # 如果没有IP，则设置为不可达
                self.connection_status[connection_key] = 0
                print(f"连接 {source_device} -> {target_device} ({enterprise}): IP配置缺失")
                
        except Exception as e:
            print(f"检查连接 {source_device} -> {target_device} 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.connection_status[connection_key] = 0
    
    def _ping_device(self, ip):
        """使用ping命令检测设备连通性"""
        try:
            # 根据操作系统选择ping命令参数
            if platform.system().lower() == "windows":
                # Windows系统使用-n参数指定发送次数，-w指定超时时间（毫秒）
                ping_cmd = ["ping", "-n", "3", "-w", "2000", ip]
            else:
                # Linux/Unix系统使用-c参数指定发送次数，-W指定超时时间（秒）
                ping_cmd = ["ping", "-c", "3", "-W", "2", ip]
            
            # 执行ping命令
            print(f"正在ping设备 {ip}...")
            result = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 检查ping命令是否成功
            success = result.returncode == 0
            print(f"Ping {ip} {'成功' if success else '失败'}")
            if not success:
                print(f"Ping输出: {result.stdout}")
            
            return success
            
        except Exception as e:
            print(f"Ping设备{ip}错误: {str(e)}")
            return False
    
    def get_connection_status(self):
        """获取当前连接状态"""
        return self.connection_status

# 单例模式，提供全局访问点
_detector_instance = None

def get_detector_instance():
    """获取检测器实例（单例模式）"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = CommunicationDetector()
    return _detector_instance