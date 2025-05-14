from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                            QPushButton, QComboBox, QMessageBox, QLabel, 
                            QGroupBox, QHBoxLayout, QProgressDialog, QTextEdit,
                            QCheckBox, QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap
from core.services.device_service import DeviceService
from .dhcp_configuration import DHCPConfigurator
import re
import os
import traceback
import time
# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class DHCPConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DHCP配置工具")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # 初始化设备选项列表
        self.device_options = []
        self.configurator = None
        
        # 创建日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #f5f5f5; font-family: Consolas, monospace;")
        
        # 加载设备数据
        self.load_device_data()
        
        # 初始化UI
        self.init_ui()
        
        # 记录日志
        self.log("DHCP配置工具已启动")
        self.log(f"已加载 {len(self.device_options)} 个设备")

    def log(self, message):
        """添加日志到日志区域"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        # 同时打印到控制台
        print(f"[DHCP] {message}")

    def load_device_data(self):
        """从数据库加载设备数据并处理成设备选项列表"""
        try:
            # 获取设备数据
            devices = DeviceService.get_all_devices()
            print(f"获取到的设备数据: {devices}")
            
            if not devices:
                print("未从数据库获取到设备")
                # 添加一些硬编码的设备作为备选
                self.add_hardcoded_devices()
                return
                
            # 处理设备数据为选项列表
            for device in devices:
                if isinstance(device, dict):
                    device_type = device.get('type', '')
                    ip = device.get('ip', '')
                    username = device.get('username', '')
                    password = device.get('password', '')
                    
                    if not device_type or not ip:
                        continue
                        
                    # 根据设备类型确定企业名称
                    enterprise = device.get('enterprise', '')
                    if not enterprise:
                        enterprise = device.get('description', '')
                    if not enterprise:
                        enterprise = "企业A"  # 默认企业名称
                        
                    # 添加到设备选项列表
                    self.device_options.append((device_type, enterprise, ip, username, password))
            
            # 如果设备列表为空，添加硬编码的设备
            if not self.device_options:
                self.add_hardcoded_devices()
                
            print(f"处理后的设备选项列表: {self.device_options}")
            
        except Exception as e:
            print(f"加载设备数据时出错: {str(e)}")
            traceback.print_exc()
            # 添加硬编码的设备作为备选
            self.add_hardcoded_devices()
    
    def add_hardcoded_devices(self):
        """添加硬编码的设备作为备选"""
        print("添加硬编码的设备作为备选")
        self.device_options = [
            ("地域1核心交换机", "企业A", "10.1.0.3", "admin", "admin123"),
            ("地域1出口路由器", "企业A", "10.1.200.1", "admin", "admin123"),
            ("地域2出口路由器", "企业A", "10.1.18.1", "admin", "admin123"),
            ("地域1汇聚交换机", "企业A", "22.22.22.22", "admin", "admin123"),
            ("地域2核心交换机", "企业A", "10.1.18.8", "admin", "admin123")
        ]

    def init_ui(self):
        """初始化用户界面"""
        # 主布局为水平分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧配置面板
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加标题
        title_label = QLabel("DHCP服务配置")
        title_label.setFont(QFont("微软雅黑", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        config_layout.addWidget(title_label)
        
        # 设备选择区域
        device_group = QGroupBox("设备选择")
        device_layout = QVBoxLayout()
        
        # 设备类型选择
        self.device_combo = QComboBox()
        self.device_combo.setFont(QFont("微软雅黑", 10))
        
        # 添加设备选项
        if self.device_options:
            for i, device_info in enumerate(self.device_options):
                device_type, enterprise = device_info[0], device_info[1]
                display_text = f"{device_type} - {enterprise} ({device_info[2]})"
                self.device_combo.addItem(display_text, device_info)
        else:
            # 如果没有设备选项，添加一个提示项
            self.device_combo.addItem("未找到可用设备", None)
            self.device_combo.setEnabled(False)
            QMessageBox.warning(self, "警告", "未找到可用设备，请确保数据库中有设备数据")
        
        # 设备信息显示
        self.device_info_label = QLabel("设备信息: 请选择设备")
        self.device_info_label.setWordWrap(True)
        self.device_combo.currentIndexChanged.connect(self.update_device_info)
        
        device_layout.addWidget(QLabel("选择设备:"))
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.device_info_label)
        device_group.setLayout(device_layout)
        config_layout.addWidget(device_group)
        
        # 配置参数输入区域
        config_group = QGroupBox("DHCP配置参数")
        form = QFormLayout()
        
        # 地址池名称
        self.pool_name = QLineEdit()
        self.pool_name.setPlaceholderText("例如: VLAN100_POOL")
        self.pool_name.setToolTip("地址池名称，用于标识DHCP地址池")
        form.addRow("地址池名称:", self.pool_name)
        
        # 网络地址
        self.network = QLineEdit()
        self.network.setPlaceholderText("例如: 192.168.1.0 255.255.255.0 或 192.168.1.0/24")
        self.network.setToolTip("DHCP分配的网络地址和掩码")
        form.addRow("网络地址:", self.network)
        
        # 排除地址
        self.excluded = QLineEdit()
        self.excluded.setPlaceholderText("例如: 192.168.1.1 192.168.1.10 (可选)")
        self.excluded.setToolTip("不希望DHCP分配的地址范围，留空表示不排除")
        form.addRow("排除地址:", self.excluded)
        
        # DNS服务器
        self.dns = QLineEdit()
        self.dns.setPlaceholderText("例如: 8.8.8.8 (可选)")
        self.dns.setToolTip("DHCP分配的DNS服务器地址，留空表示不配置")
        form.addRow("DNS服务器:", self.dns)
        
        # 高级选项
        self.advanced_options = QCheckBox("显示高级选项")
        self.advanced_options.setChecked(False)
        self.advanced_options.stateChanged.connect(self.toggle_advanced_options)
        form.addRow("", self.advanced_options)
        
        # 高级选项区域
        self.advanced_group = QGroupBox("高级选项")
        self.advanced_group.setVisible(False)
        advanced_form = QFormLayout()
        
        # 租约时间
        self.lease_time = QLineEdit("3")
        self.lease_time.setPlaceholderText("例如: 3 (天)")
        self.lease_time.setToolTip("DHCP地址租约时间，单位为天")
        advanced_form.addRow("租约时间(天):", self.lease_time)
        
        # 默认网关
        self.gateway = QLineEdit()
        self.gateway.setPlaceholderText("例如: 192.168.1.1 (可选)")
        self.gateway.setToolTip("DHCP分配的默认网关地址，留空表示不配置")
        advanced_form.addRow("默认网关:", self.gateway)
        
        # 调试模式
        self.debug_mode = QCheckBox("启用调试模式")
        self.debug_mode.setChecked(True)
        self.debug_mode.setToolTip("启用调试模式，记录详细日志")
        advanced_form.addRow("", self.debug_mode)
        
        self.advanced_group.setLayout(advanced_form)
        
        config_group.setLayout(form)
        config_layout.addWidget(config_group)
        config_layout.addWidget(self.advanced_group)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        # 清空按钮
        clear_btn = QPushButton('清空输入')
        clear_btn.setIcon(QIcon.fromTheme("edit-clear"))
        clear_btn.clicked.connect(self.clear_inputs)
        
        # 提交按钮
        submit_btn = QPushButton('应用配置')
        submit_btn.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        submit_btn.clicked.connect(self.validate_and_apply)
        
        # 刷新设备按钮
        refresh_btn = QPushButton('刷新设备列表')
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.refresh_devices)
        
        # 测试连接按钮
        test_btn = QPushButton('测试设备连接')
        test_btn.setIcon(QIcon.fromTheme("network-wired"))
        test_btn.clicked.connect(self.test_device_connection)
        
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(test_btn)
        button_layout.addWidget(submit_btn)
        config_layout.addLayout(button_layout)
        
        # 说明文本
        help_text = QLabel("注意: 网络地址支持CIDR格式(如192.168.1.0/24)或传统格式(如192.168.1.0 255.255.255.0)")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-style: italic;")
        config_layout.addWidget(help_text)
        
        # 右侧日志面板
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        log_title = QLabel("操作日志")
        log_title.setFont(QFont("微软雅黑", 12, QFont.Bold))
        log_title.setAlignment(Qt.AlignCenter)
        
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_area)
        
        # 清空日志按钮
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_area.clear)
        log_layout.addWidget(clear_log_btn)
        
        # 添加到分割器
        splitter.addWidget(config_panel)
        splitter.addWidget(log_panel)
        splitter.setSizes([400, 400])  # 设置初始大小
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)
        
        # 状态栏
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 2, 5, 2)
        
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(status_frame)
        
        # 初始化后更新设备信息
        if self.device_combo.count() > 0:
            self.update_device_info()

    def toggle_advanced_options(self, state):
        """切换高级选项的显示状态"""
        self.advanced_group.setVisible(state == Qt.Checked)
        
    def update_device_info(self):
        """更新设备信息显示"""
        device_data = self.device_combo.currentData()
        if device_data:
            device_type, enterprise, ip, username, password = device_data
            self.device_info_label.setText(f"设备信息: {device_type}\nIP地址: {ip}\n企业: {enterprise}")
            self.log(f"已选择设备: {device_type} ({ip})")
        else:
            self.device_info_label.setText("设备信息: 未选择设备")

    def test_device_connection(self):
        """测试设备连接"""
        device_data = self.device_combo.currentData()
        if device_data is None:
            QMessageBox.warning(self, "选择错误", "请选择一个有效的设备")
            return
            
        self.status_label.setText("正在测试设备连接...")
        self.log(f"正在测试设备连接...")
        
        # 显示进度对话框
        progress = QProgressDialog("正在测试设备连接...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            device_type, enterprise, ip, username, password = device_data
            
            # 获取线程工厂实例
            thread_factory = ThreadFactory.get_instance()
            
            # 使用线程工厂创建线程执行连接测试
            thread_factory.start_thread(
                target=self._perform_connection_test_thread,
                name="设备连接测试线程",
                args=(device_type, enterprise, ip, username, password),
                module="DHCP配置模块"
            )
            
        except Exception as e:
            progress.close()
            self.status_label.setText("连接测试失败")
            self.log(f"连接测试失败: {str(e)}")
            QMessageBox.critical(self, "连接错误", f"测试连接时发生错误: {str(e)}")
    
    def _perform_connection_test_thread(self, device_type, enterprise, ip, username, password):
        """在线程中执行连接测试"""
        try:
            # 创建配置器实例
            self.configurator = DHCPConfigurator(device_type, enterprise, ip, username, password)
            
            # 模拟测试连接
            time.sleep(1)  # 模拟网络延迟
            
            # 在主线程中更新UI
            from PyQt5.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_update_ui_after_connection_test", 
                                    Qt.QueuedConnection,
                                    Q_ARG(bool, True),
                                    Q_ARG(str, ip),
                                    Q_ARG(str, device_type))
            
        except Exception as e:
            # 在主线程中显示错误
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self, "_show_connection_error", 
                                    Qt.QueuedConnection,
                                    Q_ARG(str, str(e)))
    
    def _update_ui_after_connection_test(self, success, ip, device_type):
        """在主线程中更新UI"""
        # 关闭进度对话框
        for child in self.children():
            if isinstance(child, QProgressDialog):
                child.close()
                break
        
        if success:
            self.status_label.setText("连接测试成功")
            self.log(f"连接测试成功: {ip}")
            QMessageBox.information(self, "连接成功", 
                                  f"成功连接到设备\n"
                                  f"设备: {device_type}\n"
                                  f"IP: {ip}")
        else:
            self.status_label.setText("连接测试失败")
            self.log(f"连接测试失败: {ip}")
            QMessageBox.warning(self, "连接失败", f"无法连接到设备 {ip}")
    
    def _show_connection_error(self, error_message):
        """在主线程中显示错误"""
        # 关闭进度对话框
        for child in self.children():
            if isinstance(child, QProgressDialog):
                child.close()
                break
        
        self.status_label.setText("连接测试失败")
        self.log(f"连接测试失败: {error_message}")
        QMessageBox.critical(self, "连接错误", f"测试连接时发生错误: {error_message}")

    def refresh_devices(self):
        """刷新设备列表"""
        try:
            self.log("正在刷新设备列表...")
            self.status_label.setText("正在刷新设备列表...")
            
            # 清空当前设备列表
            self.device_combo.clear()
            self.device_options = []
            
            # 重新加载设备数据
            self.load_device_data()
            
            # 添加设备选项到下拉框
            if self.device_options:
                for device_info in self.device_options:
                    device_type, enterprise = device_info[0], device_info[1]
                    display_text = f"{device_type} - {enterprise} ({device_info[2]})"
                    self.device_combo.addItem(display_text, device_info)
                self.device_combo.setEnabled(True)
                self.log(f"设备列表刷新成功，共加载 {len(self.device_options)} 个设备")
                self.status_label.setText(f"已加载 {len(self.device_options)} 个设备")
                QMessageBox.information(self, "刷新成功", f"已成功刷新设备列表，共加载 {len(self.device_options)} 个设备")
            else:
                self.device_combo.addItem("未找到可用设备", None)
                self.device_combo.setEnabled(False)
                self.log("未找到可用设备")
                self.status_label.setText("未找到可用设备")
                QMessageBox.warning(self, "警告", "未找到可用设备，请确保数据库中有设备数据")
                
        except Exception as e:
            self.log(f"刷新设备列表失败: {str(e)}")
            self.status_label.setText("刷新设备列表失败")
            QMessageBox.critical(self, "刷新失败", f"刷新设备列表时出错: {str(e)}")
            print(f"刷新设备列表时出错: {str(e)}")
            traceback.print_exc()

    def clear_inputs(self):
        """清空所有输入框"""
        self.pool_name.clear()
        self.network.clear()
        self.excluded.clear()
        self.dns.clear()
        self.lease_time.setText("3")
        self.gateway.clear()
        self.log("已清空输入框")
        self.status_label.setText("已清空输入")

    def validate_and_apply(self):
        """验证输入并应用配置"""
        # 检查是否有设备选择
        device_data = self.device_combo.currentData()
        if device_data is None:
            QMessageBox.warning(self, "选择错误", "请选择一个有效的设备")
            return
            
        # 验证地址池名称
        pool_name = self.pool_name.text().strip()
        if not pool_name:
            QMessageBox.warning(self, "输入错误", "请输入地址池名称")
            self.pool_name.setFocus()
            return
            
        # 验证网络地址
        network = self.network.text().strip()
        if not network:
            QMessageBox.warning(self, "输入错误", "请输入网络地址")
            self.network.setFocus()
            return
            
        # 验证网络地址格式
        if '/' in network:  # CIDR格式
            try:
                ip, prefix = network.split('/')
                if not self.is_valid_ip(ip) or not prefix.isdigit() or int(prefix) > 32:
                    raise ValueError("无效的CIDR格式")
            except:
                QMessageBox.warning(self, "输入错误", "网络地址CIDR格式无效，请使用如192.168.1.0/24的格式")
                self.network.setFocus()
                return
        else:  # 传统格式
            parts = network.split()
            if len(parts) != 2 or not self.is_valid_ip(parts[0]) or not self.is_valid_ip(parts[1]):
                QMessageBox.warning(self, "输入错误", "网络地址格式无效，请使用如192.168.1.0 255.255.255.0的格式")
                self.network.setFocus()
                return
                
        # 验证排除地址（如果有）
        excluded = self.excluded.text().strip()
        if excluded:
            parts = excluded.split()
            if len(parts) not in (1, 2) or not all(self.is_valid_ip(p) for p in parts):
                QMessageBox.warning(self, "输入错误", "排除地址格式无效，请使用如192.168.1.1或192.168.1.1 192.168.1.10的格式")
                self.excluded.setFocus()
                return
                
        # 验证DNS服务器（如果有）
        dns = self.dns.text().strip()
        if dns and not self.is_valid_ip(dns):
            QMessageBox.warning(self, "输入错误", "DNS服务器地址格式无效")
            self.dns.setFocus()
            return
            
        # 验证高级选项
        lease_time = self.lease_time.text().strip()
        if lease_time and not lease_time.isdigit():
            QMessageBox.warning(self, "输入错误", "租约时间必须是一个整数")
            self.lease_time.setFocus()
            return
            
        gateway = self.gateway.text().strip()
        if gateway and not self.is_valid_ip(gateway):
            QMessageBox.warning(self, "输入错误", "默认网关地址格式无效")
            self.gateway.setFocus()
            return
            
        # 所有验证通过，准备应用配置
        self.log(f"开始配置DHCP: {pool_name} - {network}")
        self.status_label.setText("正在配置DHCP...")
        
        # 显示进度对话框
        progress = QProgressDialog("正在配置DHCP...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            device_type, enterprise, ip, username, password = device_data
            
            # 创建配置器实例
            if not self.configurator:
                self.configurator = DHCPConfigurator(device_type, enterprise, ip, username, password)
            
            # 获取线程工厂实例
            thread_factory = ThreadFactory.get_instance()
            
            # 使用线程工厂创建线程执行DHCP配置
            thread_factory.start_thread(
                target=self._perform_dhcp_configuration,
                name="DHCP配置线程",
                args=(progress, pool_name, network, excluded, dns, lease_time, gateway),
                module="DHCP配置模块"
            )
            
        except Exception as e:
            progress.close()
            self.status_label.setText("DHCP配置失败")
            self.log(f"DHCP配置失败: {str(e)}")
            QMessageBox.critical(self, "配置错误", f"配置DHCP时发生错误: {str(e)}")
    
    def _perform_dhcp_configuration(self, progress, pool_name, network, excluded, dns, lease_time, gateway):
        """在线程中执行DHCP配置"""
        try:
            # 执行DHCP配置
            debug_mode = self.debug_mode.isChecked()
            result = self.configurator.configure_dhcp(
                pool_name=pool_name,
                network=network,
                excluded=excluded if excluded else None,
                dns=dns if dns else None,
                lease_time=int(lease_time) if lease_time else None,
                gateway=gateway if gateway else None,
                debug=debug_mode
            )
            
            # 在主线程中更新UI，不使用invokeMethod
            from PyQt5.QtCore import QTimer, Qt
            from functools import partial
            
            # 使用QTimer在主线程中安全调用方法
            QTimer.singleShot(0, partial(self._safe_update_ui, result, pool_name))
            
        except Exception as e:
            # 记录错误
            print(f"DHCP配置过程中出现错误: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 在主线程中显示错误，使用QTimer代替invokeMethod
            from PyQt5.QtCore import QTimer
            from functools import partial
            
            # 使用QTimer在主线程中安全调用方法
            QTimer.singleShot(0, partial(self._safe_show_error, str(e), progress))
    
    def _safe_update_ui(self, result, pool_name):
        """线程安全的UI更新方法"""
        # 关闭进度对话框
        for child in self.children():
            if isinstance(child, QProgressDialog):
                child.close()
                break
        
        if result:
            self.status_label.setText("DHCP配置成功")
            self.log(f"DHCP配置成功: {pool_name}")
            QMessageBox.information(self, "配置成功", f"DHCP地址池 {pool_name} 配置成功")
        else:
            self.status_label.setText("DHCP配置失败")
            self.log(f"DHCP配置失败: {pool_name}")
            QMessageBox.warning(self, "配置失败", f"DHCP地址池 {pool_name} 配置失败，请查看日志")
    
    def _safe_show_error(self, error_message, progress=None):
        """线程安全的错误显示方法"""
        # 关闭进度对话框
        if progress:
            progress.close()
        
        # 否则检查子控件中的进度对话框
        else:
            for child in self.children():
                if isinstance(child, QProgressDialog):
                    child.close()
                    break
        
        self.status_label.setText("DHCP配置失败")
        self.log(f"DHCP配置失败: {error_message}")
        QMessageBox.critical(self, "配置错误", f"配置DHCP时发生错误: {error_message}")

    def is_valid_ip(self, ip):
        """验证IP地址格式"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        return all(0 <= int(octet) <= 255 for octet in ip.split('.'))