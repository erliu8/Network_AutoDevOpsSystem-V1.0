# login_window.py
import sys
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QMessageBox, QCheckBox,
                            QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont

# 导入用户服务
from core.services.user_service import UserService, User

class LoginWindow(QWidget):
    # 定义登录成功信号
    login_success = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化数据库
        UserService.init_db()
        self.init_ui()
        self.load_saved_username()
        
    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle('自动运维平台 - 登录')
        self.setFixedSize(540, 480)  # 略微增加窗口大小
        
        # 修改输入框样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: '微软雅黑';
            }
            QLabel {
                color: #2c3e50;
            }
            QLabel#titleLabel {
                color: #2c3e50;
                font-size: 32px;
                font-weight: bold;
                margin: 20px 0;
            }
            QLineEdit {
                padding: 18px;  /* 增加内边距 */
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 16px;
                background-color: white;
                min-height: 52px;  /* 增加最小高度 */
            }
            QLineEdit:focus {
                border: 2px solid #4dabf7;
            }
            QPushButton#loginButton {
                background-color: #4dabf7;
                color: white;
                padding: 15px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton#loginButton:hover {
                background-color: #339af0;
            }
            QCheckBox {
                font-size: 15px;
                color: #495057;
            }
            QFrame#loginFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #dee2e6;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建登录框架
        login_frame = QFrame()
        login_frame.setObjectName("loginFrame")
        login_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 登录框架布局
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(45, 45, 45, 45)  # 增加内边距
        login_layout.setSpacing(25)  # 增加组件间距
        
        # 添加标题
        title_label = QLabel('自动运维平台')
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        # 添加用户名输入框
        username_layout = QVBoxLayout()
        username_layout.setSpacing(10)  # 增加标签和输入框的间距
        username_label = QLabel('用户名')
        username_label.setFont(QFont('微软雅黑', 14))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        self.username_input.setMinimumHeight(52)  # 增加用户名输入框高度
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        login_layout.addLayout(username_layout)
        
        # 添加密码输入框
        password_layout = QVBoxLayout()
        password_layout.setSpacing(10)  # 增加标签和输入框的间距
        password_label = QLabel('密码')
        password_label.setFont(QFont('微软雅黑', 14))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(52)  # 增加密码输入框高度
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        login_layout.addLayout(password_layout)
        
        # 添加记住用户名复选框
        remember_layout = QHBoxLayout()
        self.remember_checkbox = QCheckBox('记住用户名')
        remember_layout.addWidget(self.remember_checkbox)
        remember_layout.addStretch()
        login_layout.addLayout(remember_layout)
        
        # 添加登录按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.login_button = QPushButton('登录')
        self.login_button.setObjectName("loginButton")
        self.login_button.setFixedSize(200, 50)
        self.login_button.clicked.connect(self.login)
        button_layout.addWidget(self.login_button)
        button_layout.addStretch()
        login_layout.addLayout(button_layout)
        
        # 设置回车键触发登录
        self.password_input.returnPressed.connect(self.login)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        
        # 添加登录框架到主布局
        main_layout.addWidget(login_frame)
        
        self.setLayout(main_layout)
        
    def load_saved_username(self):
        """加载保存的用户名"""
        settings = QSettings("AutoDevOps", "LoginInfo")
        saved_username = settings.value("username", "")
        if saved_username:
            self.username_input.setText(saved_username)
            self.remember_checkbox.setChecked(True)
            self.password_input.setFocus()
        else:
            self.username_input.setFocus()
            
    def save_username(self, username):
        """保存用户名"""
        settings = QSettings("AutoDevOps", "LoginInfo")
        if self.remember_checkbox.isChecked():
            settings.setValue("username", username)
        else:
            settings.setValue("username", "")
            
    def login(self):
        """处理登录逻辑"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "登录失败", "用户名和密码不能为空")
            return
        
        # 使用UserService验证用户
        success, user = UserService.authenticate_user(username, password)
        
        if not success:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
            self.password_input.clear()
            self.password_input.setFocus()
            return
        
        # 检查权限
        if user["role"] != "admin":
            QMessageBox.warning(self, "权限不足", "只有管理员用户才能登录系统")
            return
        
        # 登录成功
        print(f"用户 {username} 登录成功")
        self.save_username(username)
        self.login_success.emit()
        self.close()

# 测试代码
if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())