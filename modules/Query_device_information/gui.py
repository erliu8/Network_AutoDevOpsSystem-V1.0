import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QPushButton, QTextEdit, 
                            QProgressDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot
import threading

# 导入查询服务
from core.business.query_service import QueryService
from .Query_device_information import DEVICE_DATA, PREDEFINED_COMMANDS

class DeviceInfoQueryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("设备信息查询工具")
        self.setMinimumSize(800, 600)
        
        # 使用查询服务替代直接使用DeviceConnector
        self.query_service = QueryService()
        self.query_service.connection_result.connect(self.handle_connection_result)
        self.query_service.command_result.connect(self.handle_command_result)
        
        self.progress_dialog = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 设备选择区域
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("设备类型:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(DEVICE_DATA.keys())
        device_layout.addWidget(self.device_combo)
        
        device_layout.addWidget(QLabel("企业:"))
        self.enterprise_combo = QComboBox()
        self.enterprise_combo.addItem("")  # 空选项
        self.enterprise_combo.addItem("企业A")
        self.enterprise_combo.addItem("企业B")
        device_layout.addWidget(self.enterprise_combo)
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.connect_device)
        device_layout.addWidget(self.connect_btn)
        
        main_layout.addLayout(device_layout)
        
        # 命令选择区域
        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("预定义命令:"))
        self.command_combo = QComboBox()
        self.command_combo.addItems(PREDEFINED_COMMANDS.keys())
        command_layout.addWidget(self.command_combo)
        
        self.execute_btn = QPushButton("执行")
        self.execute_btn.clicked.connect(self.execute_predefined)
        command_layout.addWidget(self.execute_btn)
        
        main_layout.addLayout(command_layout)
        
        # 自定义命令区域
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("自定义命令:"))
        self.custom_command = QTextEdit()
        self.custom_command.setMaximumHeight(60)
        custom_layout.addWidget(self.custom_command)
        
        self.custom_btn = QPushButton("执行")
        self.custom_btn.clicked.connect(self.execute_custom)
        custom_layout.addWidget(self.custom_btn)
        
        main_layout.addLayout(custom_layout)
        
        # 结果显示区域
        main_layout.addWidget(QLabel("执行结果:"))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        main_layout.addWidget(self.result_text)
        
        self.setLayout(main_layout)
        
    def connect_device(self):
        """连接到设备"""
        device_text = self.device_combo.currentText()
        enterprise = self.enterprise_combo.currentText()
        
        # 处理地域1核心交换机的特殊情况
        if "地域1核心交换机" in device_text and not enterprise:
            enterprise = "企业A"
        
        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在连接设备...", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        
        # 使用查询服务连接设备
        self.query_service.connect_device(device_text, enterprise)
        
    @pyqtSlot(bool, str)
    def handle_connection_result(self, success, message):
        """处理连接结果"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        if success:
            self.result_text.append(f"<span style='color:green'>✓ 连接成功: {message}</span>")
            self.connect_btn.setText("已连接")
            self.connect_btn.setEnabled(False)
        else:
            self.result_text.append(f"<span style='color:red'>✗ 连接失败: {message}</span>")
            QMessageBox.critical(self, "连接失败", message)
            
    def execute_predefined(self):
        """执行预定义命令"""
        device = self.device_combo.currentText()
        enterprise = self.enterprise_combo.currentText()
        command_name = self.command_combo.currentText()
        command = PREDEFINED_COMMANDS[command_name]
        
        # 创建进度对话框
        self.progress_dialog = QProgressDialog(f"正在执行命令: {command_name}...", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        
        # 在结果区域显示正在执行的命令
        self.result_text.append(f"\n[命令] {command}")
        
        # 使用查询服务执行命令
        self.query_service.execute_command(device, enterprise, command)
        
    def execute_custom(self):
        """执行自定义命令"""
        device = self.device_combo.currentText()
        enterprise = self.enterprise_combo.currentText()
        command = self.custom_command.toPlainText().strip()
        
        if not command:
            QMessageBox.warning(self, "警告", "请输入命令")
            return
            
        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在执行命令...", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        
        # 在结果区域显示正在执行的命令
        self.result_text.append(f"\n[命令] {command}")
        
        # 使用查询服务执行命令
        self.query_service.execute_command(device, enterprise, command)
        
    @pyqtSlot(str)
    def handle_command_result(self, result):
        """处理命令执行结果"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        # 在结果区域显示命令输出
        self.result_text.append(f"[输出]\n{result}")
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 清理资源
        self.query_service.cleanup()
        event.accept()

# 如果需要独立测试 gui.py
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DeviceInfoQueryWindow()
    window.show()
    sys.exit(app.exec_())