from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QLabel, QMessageBox, 
                             QHeaderView, QSplitter, QFrame, QTextEdit, QComboBox,
                             QToolBar, QAction, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QCheckBox, QGroupBox, QProgressDialog)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
import requests
import json
import time
import traceback
from datetime import datetime
import os

# 导入任务队列
from core.business.task_queue import TaskQueue

class ApprovalWindow(QWidget):
    """任务审批窗口"""
    
    # 定义信号
    task_approved = pyqtSignal(str)  # 任务ID
    task_rejected = pyqtSignal(str)  # 任务ID
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("任务审批")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        # 获取任务队列
        self.task_queue = None
        self.get_task_queue()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化定时器（用于自动刷新任务列表）
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_tasks)
        self.refresh_timer.start(5000)  # 每5秒刷新一次
        
        # 首次加载任务
        QTimer.singleShot(500, self.refresh_tasks)
        
    def get_task_queue(self):
        """获取任务队列实例"""
        try:
            # 尝试从DBTaskQueue获取实例
            try:
                from core.business.db_task_queue import get_db_task_queue
                self.task_queue = get_db_task_queue()
                print("成功获取数据库任务队列实例")
            except ImportError:
                # 回退到内存任务队列
                from core.business.task_queue import TaskQueue
                self.task_queue = TaskQueue()
                print("回退到内存任务队列实例")
            
            # 连接信号
            self.task_approved.connect(self.on_task_approved)
            self.task_rejected.connect(self.on_task_rejected)
            
            return True
        except Exception as e:
            print(f"获取任务队列实例失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def init_ui(self):
        """初始化用户界面"""
        # 初始化复选框属性
        self.debug_mode = QCheckBox("启用调试模式")
        self.debug_mode.setChecked(False)  # 默认关闭调试模式，确保命令真正执行
        self.debug_mode.setToolTip("启用调试模式，记录详细日志")
        
        # 添加测试设备模式复选框
        self.test_device_mode = QCheckBox("使用测试设备模式")
        self.test_device_mode.setChecked(True)  # 默认启用测试设备模式
        self.test_device_mode.setToolTip("使用测试设备模式，不需要真实设备也能执行命令")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QToolBar("工具栏")
        toolbar.setIconSize(QSize(24, 24))
        
        # 刷新按钮
        refresh_action = QAction(QIcon.fromTheme("view-refresh"), "刷新任务", self)
        refresh_action.triggered.connect(self.refresh_tasks)
        toolbar.addAction(refresh_action)
        
        # 批准按钮
        approve_action = QAction(QIcon.fromTheme("dialog-ok-apply"), "批准选中任务", self)
        approve_action.triggered.connect(self.approve_selected_task)
        toolbar.addAction(approve_action)
        
        # 拒绝按钮
        reject_action = QAction(QIcon.fromTheme("dialog-cancel"), "拒绝选中任务", self)
        reject_action.triggered.connect(self.reject_selected_task)
        toolbar.addAction(reject_action)
        
        # 状态筛选
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("状态筛选: "))
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部")
        self.status_filter.addItem("待审核")
        self.status_filter.addItem("已审核")
        self.status_filter.addItem("已拒绝")
        self.status_filter.addItem("已完成")
        self.status_filter.addItem("执行失败")
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.status_filter)
        
        # 类型筛选
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("任务类型: "))
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部")
        self.type_filter.addItem("DHCP配置")
        self.type_filter.addItem("路由配置")
        self.type_filter.addItem("其他")
        self.type_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.type_filter)
        
        main_layout.addWidget(toolbar)
        
        # 分隔器
        splitter = QSplitter(Qt.Vertical)
        
        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels(["ID", "任务类型", "状态", "创建时间", "发起者", "处理时间", "操作"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.itemSelectionChanged.connect(self.on_task_selected)
        
        # 设置行高
        self.task_table.verticalHeader().setDefaultSectionSize(36)
        
        splitter.addWidget(self.task_table)
        
        # 任务详情面板
        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        
        details_title = QLabel("任务详情")
        details_title.setFont(QFont("微软雅黑", 10, QFont.Bold))
        details_layout.addWidget(details_title)
        
        # 详情内容分为左右两部分
        details_content = QWidget()
        details_content_layout = QHBoxLayout(details_content)
        
        # 左侧基本信息
        left_panel = QWidget()
        left_layout = QFormLayout(left_panel)
        
        self.detail_task_id = QLabel("-")
        self.detail_task_type = QLabel("-")
        self.detail_status = QLabel("-")
        self.detail_created_at = QLabel("-")
        self.detail_requester = QLabel("-")
        
        left_layout.addRow("任务ID:", self.detail_task_id)
        left_layout.addRow("任务类型:", self.detail_task_type)
        left_layout.addRow("状态:", self.detail_status)
        left_layout.addRow("创建时间:", self.detail_created_at)
        left_layout.addRow("请求者:", self.detail_requester)
        
        # 右侧参数信息
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("任务参数:"))
        self.detail_params = QTextEdit()
        self.detail_params.setReadOnly(True)
        right_layout.addWidget(self.detail_params)
        
        details_content_layout.addWidget(left_panel, 1)
        details_content_layout.addWidget(right_panel, 2)
        details_layout.addWidget(details_content)
        
        # 添加选项区域
        options_group = QGroupBox("执行选项")
        options_layout = QHBoxLayout()
        
        # 添加debug模式和测试设备模式复选框
        options_layout.addWidget(self.debug_mode)
        options_layout.addWidget(self.test_device_mode)
        
        options_group.setLayout(options_layout)
        details_layout.addWidget(options_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.approve_button = QPushButton("批准任务")
        self.approve_button.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        self.approve_button.clicked.connect(self.approve_selected_task)
        self.approve_button.setEnabled(False)
        
        self.reject_button = QPushButton("拒绝任务")
        self.reject_button.setIcon(QIcon.fromTheme("dialog-cancel"))
        self.reject_button.clicked.connect(self.reject_selected_task)
        self.reject_button.setEnabled(False)
        
        button_layout.addWidget(self.approve_button)
        button_layout.addWidget(self.reject_button)
        details_layout.addLayout(button_layout)
        
        splitter.addWidget(details_panel)
        
        # 设置分隔比例
        splitter.setSizes([400, 200])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
    
    def refresh_tasks(self):
        """刷新任务列表"""
        self.status_label.setText("正在加载任务...")
        
        try:
            print("\n[DEBUG] 审批窗口开始刷新任务列表...")
            if not self.task_queue:
                print("[DEBUG] 任务队列未初始化，尝试获取任务队列...")
                self.get_task_queue()
                if not self.task_queue:
                    print("[ERROR] 无法获取任务队列实例")
                    self.status_label.setText("无法获取任务队列实例")
                    return
                print(f"[DEBUG] 获取任务队列类型: {type(self.task_queue).__name__}")
            
            # 主动触发一次轮询，确保获取最新任务
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    if hasattr(self.task_queue, 'poll_task_status_changes'):
                        print("[DEBUG] 主动调用轮询获取最新任务状态...")
                        self.task_queue.poll_task_status_changes()
                        # 成功轮询，退出重试循环
                        break
                except Exception as poll_error:
                    print(f"[ERROR] 轮询任务状态失败 (尝试 {retry_count+1}/{max_retries}): {str(poll_error)}")
                    retry_count += 1
                    import time
                    time.sleep(0.5)  # 短暂等待后重试
            
            # 直接从数据库获取所有任务
            try:
                print("[DEBUG] 直接从数据库获取所有任务...")
                from shared.db.task_repository import get_task_repository
                task_repo = get_task_repository()
                tasks = task_repo.get_all_tasks(limit=100)
                print(f"[DEBUG] 直接从数据库获取到 {len(tasks)} 个任务")
                
                # 清空现有任务列表
                self.task_table.setRowCount(0)
                
                # 任务状态统计
                status_counts = {}
                for task_data in tasks:
                    status = task_data['status']
                    if status not in status_counts:
                        status_counts[status] = 0
                    status_counts[status] += 1
                
                print(f"[DEBUG] 任务状态统计: {status_counts}")
                
                # 转换为Task对象
                from core.business.db_task_queue import Task
                task_objects = []
                for task_data in tasks:
                    task_objects.append(Task.from_db_row(task_data))
                
                self.display_tasks(task_objects)
                print("[DEBUG] 任务刷新完成")
                
            except Exception as db_error:
                print(f"[ERROR] 直接从数据库获取任务失败: {str(db_error)}")
                import traceback
                traceback.print_exc()
                
                # 尝试从任务队列的内存缓存获取任务
                try:
                    if hasattr(self.task_queue, '_tracked_tasks') and self.task_queue._tracked_tasks:
                        tasks = list(self.task_queue._tracked_tasks.values())
                        print(f"[DEBUG] 从任务队列内存缓存获取到 {len(tasks)} 个任务")
                        self.display_tasks(tasks)
                except Exception as cache_error:
                    print(f"[ERROR] 从任务队列内存缓存获取任务失败: {str(cache_error)}")
                    self.status_label.setText("刷新任务失败，请重试")
            
        except Exception as e:
            print(f"[ERROR] 刷新任务列表出错: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText("刷新任务失败，请重试")
    
    def display_tasks(self, tasks):
        """显示任务列表
        
        Args:
            tasks: Task对象列表
        """
        # 清空现有任务列表
        self.task_table.setRowCount(0)
        
        if not tasks:
            self.status_label.setText("没有任务")
            return
            
        # 按时间戳排序，最新的在前面
        sorted_tasks = sorted(tasks, key=lambda t: t.created_at if t.created_at else datetime.now(), reverse=True)
        
        # 添加行
        for task in sorted_tasks:
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(task.task_id[:8])
            id_item.setData(Qt.UserRole, task.task_id)
            self.task_table.setItem(row, 0, id_item)
            
            # 任务类型
            type_map = {
                "dhcp_config": "DHCP配置",
                "route_config": "路由配置"
            }
            task_type = type_map.get(task.task_type, task.task_type)
            self.task_table.setItem(row, 1, QTableWidgetItem(task_type))
            
            # 状态
            status_map = {
                "pending": "等待中",
                "pending_approval": "待审核",
                "approved": "已审核",
                "rejected": "已拒绝",
                "running": "执行中",
                "completed": "已完成",
                "failed": "失败"
            }
            status_item = QTableWidgetItem(status_map.get(task.status, task.status))
            
            # 设置状态样式
            if task.status == "completed":
                status_item.setForeground(Qt.darkGreen)
            elif task.status == "failed" or task.status == "rejected":
                status_item.setForeground(Qt.red)
            elif task.status == "pending_approval":
                status_item.setForeground(Qt.blue)
            
            self.task_table.setItem(row, 2, status_item)
            
            # 创建时间
            created_at = task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else "-"
            self.task_table.setItem(row, 3, QTableWidgetItem(created_at))
            
            # 发起者
            requester = task.params.get("requested_by", "-") if isinstance(task.params, dict) else "-"
            self.task_table.setItem(row, 4, QTableWidgetItem(requester))
            
            # 处理时间
            completed_at = task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else "-"
            self.task_table.setItem(row, 5, QTableWidgetItem(completed_at))
            
            # 操作按钮
            if task.status == "pending_approval":
                button_cell = QWidget()
                button_layout = QHBoxLayout(button_cell)
                button_layout.setContentsMargins(3, 3, 3, 3)
                
                approve_btn = QPushButton("批准")
                approve_btn.setProperty("task_id", task.task_id)
                approve_btn.clicked.connect(lambda checked, tid=task.task_id: self.task_approved.emit(tid))
                
                reject_btn = QPushButton("拒绝")
                reject_btn.setProperty("task_id", task.task_id)
                reject_btn.clicked.connect(lambda checked, tid=task.task_id: self.task_rejected.emit(tid))
                
                button_layout.addWidget(approve_btn)
                button_layout.addWidget(reject_btn)
                
                self.task_table.setCellWidget(row, 6, button_cell)
            else:
                self.task_table.setItem(row, 6, QTableWidgetItem("-"))
    
    def apply_filters(self):
        """应用过滤器"""
        self.refresh_tasks()
    
    def on_task_selected(self):
        """当选择任务时"""
        selected_rows = self.task_table.selectedItems()
        if not selected_rows:
            self.clear_task_details()
            return
        
        # 获取任务ID
        task_id_item = self.task_table.item(selected_rows[0].row(), 0)
        if not task_id_item:
            return
        
        task_id = task_id_item.data(Qt.UserRole)
        if not task_id:
            return
        
        # 获取任务详情
        self.show_task_details(task_id)
    
    def show_task_details(self, task_id):
        """显示任务详情
        
        Args:
            task_id: 任务ID
        """
        if not self.task_queue:
            return
        
        task = self.task_queue.get_task(task_id)
        if not task:
            self.clear_task_details()
            return
        
        # 更新基本信息
        self.detail_task_id.setText(task.task_id)
        
        type_map = {
            "dhcp_config": "DHCP配置",
            "route_config": "路由配置"
        }
        task_type = type_map.get(task.task_type, task.task_type)
        self.detail_task_type.setText(task_type)
        
        status_map = {
            "pending": "等待中",
            "pending_approval": "待审核",
            "approved": "已审核",
            "rejected": "已拒绝",
            "running": "执行中",
            "completed": "已完成",
            "failed": "失败"
        }
        self.detail_status.setText(status_map.get(task.status, task.status))
        
        self.detail_created_at.setText(task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else "-")
        
        requester = task.params.get("requested_by", "-") if isinstance(task.params, dict) else "-"
        self.detail_requester.setText(requester)
        
        # 更新参数信息
        if isinstance(task.params, dict):
            # 根据任务类型格式化参数
            if task.task_type == "dhcp_config":
                self.format_dhcp_params(task.params)
            else:
                # 通用格式化
                self.detail_params.setText(json.dumps(task.params, indent=2, ensure_ascii=False))
        else:
            self.detail_params.setText(str(task.params))
        
        # 启用/禁用操作按钮
        self.approve_button.setEnabled(task.status == "pending_approval")
        self.reject_button.setEnabled(task.status == "pending_approval")
    
    def format_dhcp_params(self, params):
        """格式化DHCP参数
        
        Args:
            params: DHCP参数
        """
        from shared.db.device_repository import get_device_repository
        
        formatted = "DHCP配置参数:\n\n"
        
        # 基本参数
        formatted += f"池名称: {params.get('pool_name', '-')}\n"
        formatted += f"网络地址: {params.get('network', '-')}\n"
        formatted += f"子网掩码: {params.get('mask', '-')}\n"
        
        # 可选参数
        if params.get('gateway'):
            formatted += f"默认网关: {params.get('gateway')}\n"
        if params.get('dns'):
            formatted += f"DNS服务器: {params.get('dns')}\n"
        if params.get('domain'):
            formatted += f"域名: {params.get('domain')}\n"
        
        formatted += f"租约时间: {params.get('lease_days', 1)} 天\n"
        
        # 设备信息 - 改进设备信息显示
        device_ids = params.get('device_ids', [])
        formatted += "\n设备信息:\n"
        
        # 获取设备仓库
        device_repo = get_device_repository()
        
        if device_ids:
            for device_id in device_ids:
                # 获取设备详细信息
                device = device_repo.get_device_by_id(device_id)
                if device:
                    formatted += f"- {device.get('name', '未命名')} ({device.get('ip', '无IP')})\n"
                else:
                    formatted += f"- 设备ID: {device_id} (未找到设备信息)\n"
        else:
            formatted += "- 未指定设备\n"
        
        # 请求信息
        formatted += f"\n请求时间: {datetime.fromtimestamp(params.get('requested_at', 0)).strftime('%Y-%m-%d %H:%M:%S')}\n"
        formatted += f"请求者: {params.get('requested_by', '-')}\n"
        
        self.detail_params.setText(formatted)
    
    def clear_task_details(self):
        """清空任务详情"""
        self.detail_task_id.setText("-")
        self.detail_task_type.setText("-")
        self.detail_status.setText("-")
        self.detail_created_at.setText("-")
        self.detail_requester.setText("-")
        self.detail_params.setText("")
        
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
    
    def approve_selected_task(self):
        """批准选中的任务"""
        selected_rows = self.task_table.selectedItems()
        if not selected_rows:
            return
        
        # 获取任务ID
        task_id_item = self.task_table.item(selected_rows[0].row(), 0)
        if not task_id_item:
            return
        
        task_id = task_id_item.data(Qt.UserRole)
        if not task_id:
            return
        
        # 确认
        reply = QMessageBox.question(
            self, 
            "确认批准", 
            f"确定要批准任务 {task_id[:8]} 吗？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.task_approved.emit(task_id)
    
    def reject_selected_task(self):
        """拒绝选中的任务"""
        selected_rows = self.task_table.selectedItems()
        if not selected_rows:
            return
        
        # 获取任务ID
        task_id_item = self.task_table.item(selected_rows[0].row(), 0)
        if not task_id_item:
            return
        
        task_id = task_id_item.data(Qt.UserRole)
        if not task_id:
            return
        
        # 确认
        reply = QMessageBox.question(
            self, 
            "确认拒绝", 
            f"确定要拒绝任务 {task_id[:8]} 吗？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.task_rejected.emit(task_id)
    
    def on_task_approved(self, task_id):
        """当任务被批准时
        
        Args:
            task_id: 任务ID
        """
        try:
            # 获取任务
            from shared.db.task_repository import get_task_repository
            task_repo = get_task_repository()
            task_data = task_repo.get_task(task_id)
            
            if not task_data:
                QMessageBox.warning(self, "错误", f"找不到任务 {task_id[:8]}")
                return
            
            # 转换为Task对象，方便处理
            from core.business.db_task_queue import Task
            task = Task.from_db_row(task_data)
            
            print(f"[INFO] 批准任务: {task_id} (类型: {task.task_type})")
            
            # 确保任务处于待审批状态
            if task.status != "pending_approval":
                QMessageBox.warning(
                    self, 
                    "无法批准", 
                    f"只能批准待审批状态的任务。当前状态: {task.status}"
                )
                return
                
            # 更新任务状态
            update_success = task_repo.update_task_status(
                task_id, 
                "approved", 
                by="审批界面"
            )
            
            if not update_success:
                QMessageBox.warning(self, "错误", "更新任务状态失败")
                return
                
            # 刷新UI
            self.refresh_tasks()
            
            # 显示成功消息
            QMessageBox.information(self, "成功", f"任务 {task_id[:8]} 已被批准")
            
            # 可选: 手动处理任务
            if task.task_type == "dhcp_config":
                reply = QMessageBox.question(
                    self,
                    "处理任务",
                    "任务已被批准。是否立即处理该任务？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # 处理DHCP配置任务
                    self.handle_dhcp_task(task)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"批准任务失败: {str(e)}")
            print(f"[ERROR] 批准任务失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_task_rejected(self, task_id):
        """当任务被拒绝时
        
        Args:
            task_id: 任务ID
        """
        try:
            # 获取任务
            task = self.task_queue.get_task(task_id)
            if not task:
                QMessageBox.warning(self, "错误", f"找不到任务 {task_id[:8]}")
                return
            
            print(f"[INFO] 拒绝任务: {task_id} (类型: {task.task_type})")
            
            # 更新任务状态
            try:
                from shared.db.task_repository import get_task_repository
                task_repo = get_task_repository()
                task_repo.update_task_status(
                    task_id, 
                    "rejected", 
                    error="管理员拒绝了该任务", 
                    by="审批界面"
                )
                print(f"[INFO] 任务 {task_id} 状态已更新为 rejected")
                
                # 如果有DBTaskQueue实例，手动触发轮询以确保状态变更被检测到
                if hasattr(self.task_queue, 'poll_task_status_changes'):
                    print(f"[DEBUG] 手动触发轮询以检测状态变更")
                    self.task_queue.poll_task_status_changes()
                    
            except Exception as e:
                print(f"[ERROR] 更新任务状态失败: {str(e)}")
                traceback.print_exc()
                QMessageBox.critical(self, "错误", f"更新任务状态失败: {str(e)}")
                return
            
            # 刷新任务列表
            self.refresh_tasks()
            
            QMessageBox.information(self, "提示", f"任务 {task_id[:8]} 已被拒绝")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"拒绝任务时出错: {str(e)}")
            print(f"[ERROR] 拒绝任务出错: {str(e)}")
            traceback.print_exc()
    
    def handle_dhcp_task(self, task):
        """处理DHCP任务
        
        Args:
            task: 任务对象
        """
        # 获取DHCP配置参数
        params = task.params
        if not params:
            QMessageBox.warning(self, "错误", "任务参数为空")
            return
        
        print(f"[INFO] 处理DHCP任务: {task.task_id}")
        print(f"[DEBUG] 任务参数: {params}")
        
        # 显示进度对话框
        progress = QProgressDialog("正在处理DHCP配置任务...", "取消", 0, 100, self)
        progress.setWindowTitle("处理中")
        progress.setModal(True)
        progress.setValue(10)
        progress.show()
        
        try:
            # 从数据库获取最新任务状态
            from shared.db.task_repository import get_task_repository
            task_repo = get_task_repository()
            
            # 更新任务状态为running
            task_repo.update_task_status(
                task.task_id,
                "running",
                by="审批窗口"
            )
            
            # 获取设备ID列表
            device_ids = params.get('device_ids', [])
            if not device_ids:
                QMessageBox.warning(self, "错误", "未指定设备ID")
                progress.cancel()
                return
                
            progress.setValue(20)
            
            # 从数据库获取设备信息
            from core.repositories.device_repository import DeviceRepository
            device_repo = DeviceRepository()
            
            # 获取设备管理器
            from core.business.device_manager import get_device_manager
            device_manager = get_device_manager()
            
            progress.setValue(30)
            
            # 构建基础DHCP配置参数
            pool_name = params.get('pool_name')
            network = params.get('network')
            mask = params.get('mask')
            
            if not pool_name or not network or not mask:
                QMessageBox.warning(self, "错误", "缺少必要的DHCP配置参数")
                progress.cancel()
                
                # 更新任务状态为失败
                task_repo.update_task_status(
                    task.task_id,
                    "failed",
                    error="缺少必要的DHCP配置参数",
                    by="审批窗口"
                )
                return
            
            # 准备DHCP配置
            dhcp_configs = {
                'pool_name': pool_name,
                'network': f"{network} {mask}",  # 网络参数需要包含掩码
                'gateway': params.get('gateway'),
                'dns': params.get('dns'),
                'domain': params.get('domain'),
                'lease_time': params.get('lease_days', 1),  # 使用正确的键名 lease_time
                'debug': False  # 确保关闭调试模式，这样命令才会真正执行
            }
            
            print(f"[DEBUG] DHCP配置: {dhcp_configs}")
            
            # 准备处理结果
            device_results = []
            success_count = 0
            failure_count = 0
            
            # 连接设备管理器的信号 (在循环外连接一次)
            def on_operation_log(message):
                print(f"[设备日志] {message}")
            
            def on_operation_status(success, message):
                print(f"[设备状态] 成功={success}, 消息={message}")
                # 不在这里更新计数，避免重复计数
            
            # 连接信号
            device_manager.operation_log.connect(on_operation_log)
            device_manager.operation_status.connect(on_operation_status)
            
            # 检查或创建测试设备，以确保有可用的设备
            try:
                # 获取设备列表
                all_devices = device_repo.get_all_devices()
                if not all_devices:
                    # 创建测试设备
                    print("[DEBUG] 数据库中没有设备，创建测试设备...")
                    test_device = {
                        'name': 'Test Device',
                        'ip': '192.168.1.1',  # 测试IP - 注意更改为您的网络环境中有效的IP
                        'username': '1',
                        'password': '1',
                        'device_type': 'huawei_telnet',
                        'enterprise': 'Test',
                        'description': '测试用设备'
                    }
                    device_repo.create_device(test_device)
                    print(f"[DEBUG] 已创建测试设备: {test_device}")
                    
                    # 重新获取设备列表
                    all_devices = device_repo.get_all_devices()
                
                print(f"[DEBUG] 数据库中的设备列表: {all_devices}")
                
                # 检查是否需要将device_ids中的数字ID转换为实际设备
                new_device_ids = []
                for device_id in device_ids:
                    # 如果device_id只是数字，并且设备列表非空，使用列表中第一个设备
                    if str(device_id).isdigit() and len(all_devices) > 0:
                        if int(device_id) <= len(all_devices):
                            # 使用对应的设备
                            device_index = int(device_id) - 1
                            real_device_id = all_devices[device_index]['id']
                            print(f"[DEBUG] 将设备ID {device_id} 映射到实际设备ID {real_device_id}")
                            new_device_ids.append(real_device_id)
                        else:
                            # 使用第一个设备
                            real_device_id = all_devices[0]['id']
                            print(f"[DEBUG] 设备ID {device_id} 超出范围，使用第一个设备ID {real_device_id}")
                            new_device_ids.append(real_device_id)
                
                # 如果有新的device_ids，使用它们
                if new_device_ids:
                    print(f"[DEBUG] 原始设备ID列表: {device_ids}")
                    print(f"[DEBUG] 转换后的设备ID列表: {new_device_ids}")
                    device_ids = new_device_ids
            except Exception as e:
                print(f"[ERROR] 检查/创建测试设备时出错: {str(e)}")
                traceback.print_exc()
            
            # 循环处理每个设备
            for i, device_id in enumerate(device_ids):
                try:
                    # 更新进度
                    progress_val = 30 + int((i / len(device_ids)) * 60)
                    progress.setValue(progress_val)
                    progress.setLabelText(f"配置设备 {i+1}/{len(device_ids)}...")
                    
                    # 处理取消
                    if progress.wasCanceled():
                        break
                    
                    # 获取设备信息
                    device = device_repo.get_device_by_id(device_id)
                    print(f"[DEBUG] 查询设备 ID={device_id} 的结果: {device}")
                    if not device:
                        # 尝试查找所有设备以查看数据库连接是否正常
                        all_devices = device_repo.get_all_devices()
                        print(f"[DEBUG] 数据库中所有设备: {all_devices}")
                        
                        error_msg = f"未找到设备 ID: {device_id}"
                        print(f"[ERROR] {error_msg}")
                        device_results.append({
                            "device_id": device_id,
                            "status": "error",
                            "message": error_msg
                        })
                        failure_count += 1
                        continue
                    
                    # 获取设备连接信息
                    device_ip = device.get('ip')
                    device_name = device.get('name', f"设备{device_id}")
                    username = device.get('username', '1')  # 默认用户名
                    password = device.get('password', '1')  # 默认密码
                    
                    print(f"[INFO] 准备配置设备 {device_name} ({device_ip})")
                    
                    # 使用设备管理器配置DHCP
                    try:
                        # 确保使用正确的参数调用device_manager.configure_dhcp
                        print(f"[DEBUG] 调用 device_manager.configure_dhcp:")
                        print(f"[DEBUG] - device_ip: {device_ip}")
                        print(f"[DEBUG] - username: {username}")
                        print(f"[DEBUG] - password: {'*'*len(password)}")
                        print(f"[DEBUG] - dhcp_configs: {dhcp_configs}")
                        
                        # 真正的调用设备管理器
                        device_manager.configure_dhcp(
                            device_ip,     # 第一个参数是设备IP
                            username,      # 第二个参数是用户名
                            password,      # 第三个参数是密码
                            dhcp_configs,  # 第四个参数是DHCP配置
                            self.test_device_mode.isChecked()  # 第五个参数是否使用测试设备模式
                        )
                        
                        # 设置成功
                        success_count += 1
                        device_results.append({
                            "device_id": device_id,
                            "device_ip": device_ip,
                            "device_name": device_name,
                            "status": "success",
                            "message": f"已在设备 {device_name} ({device_ip}) 上配置DHCP: 池名称={pool_name}, 网络={network}/{mask}"
                        })
                        print(f"[INFO] 设备 {device_name} ({device_ip}) DHCP配置请求已发送")
                        
                    except Exception as e:
                        error_msg = f"设备操作失败: {str(e)}"
                        print(f"[ERROR] {error_msg}")
                        traceback.print_exc()
                        device_results.append({
                            "device_id": device_id,
                            "device_ip": device_ip,
                            "device_name": device_name,
                            "status": "error",
                            "message": error_msg
                        })
                        failure_count += 1
                        
                except Exception as e:
                    print(f"[ERROR] 设备 {device_id} 配置失败: {str(e)}")
                    traceback.print_exc()
                    
                    device_results.append({
                        "device_id": device_id,
                        "status": "error",
                        "message": f"配置出错: {str(e)}"
                    })
                    failure_count += 1
            
            # 更新任务状态
            if progress.wasCanceled():
                # 如果被取消，更新任务状态为失败
                task_repo.update_task_status(
                    task.task_id,
                    "failed",
                    error="用户取消操作",
                    by="审批窗口"
                )
                
                QMessageBox.warning(self, "取消", "DHCP配置任务已取消")
            else:
                # 设置最终状态
                final_status = "completed" if failure_count == 0 else "completed_with_errors"
                if success_count == 0:
                    final_status = "failed"
                
                # 更新任务状态为完成
                task_repo.update_task_status(
                    task.task_id,
                    final_status,
                    result={
                        "message": f"DHCP配置任务已处理，成功: {success_count}，失败: {failure_count}",
                        "device_results": device_results
                    },
                    by="审批窗口"
                )
                
                # 显示结果消息
                if final_status == "completed":
                    QMessageBox.information(
                        self, 
                        "成功", 
                        f"DHCP配置任务已成功完成，共处理 {len(device_ids)} 个设备"
                    )
                elif final_status == "completed_with_errors":
                    QMessageBox.warning(
                        self,
                        "部分成功",
                        f"DHCP配置任务已完成，但部分设备出错。成功: {success_count}，失败: {failure_count}"
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "失败",
                        f"DHCP配置任务失败，所有 {len(device_ids)} 个设备配置均失败"
                    )
            
            # 完成进度对话框
            progress.setValue(100)
            
            # 断开信号，防止内存泄漏
            device_manager.operation_log.disconnect(on_operation_log)
            device_manager.operation_status.disconnect(on_operation_status)
            
            # 刷新任务列表
            self.refresh_tasks()
            
        except Exception as e:
            progress.cancel()
            print(f"[ERROR] 处理DHCP任务失败: {str(e)}")
            traceback.print_exc()
            
            QMessageBox.critical(self, "错误", f"处理DHCP任务失败: {str(e)}")
            
            # 更新任务状态为失败
            try:
                from shared.db.task_repository import get_task_repository
                task_repo = get_task_repository()
                task_repo.update_task_status(
                    task.task_id,
                    "failed",
                    error=str(e),
                    by="审批窗口"
                )
            except Exception as update_error:
                print(f"[ERROR] 更新任务状态失败: {str(update_error)}")
                traceback.print_exc()