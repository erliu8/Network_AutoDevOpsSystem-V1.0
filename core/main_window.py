# main_window.py
from PyQt5.QtWidgets import (QMainWindow, QAction, QMenu, QToolBar, QTabWidget, 
                            QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                            QStackedWidget, QScrollArea, QFrame, QSizePolicy, QSplitter)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize, QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("校园网络自动化运维系统")
        self.setMinimumSize(1024, 768)
        
        # 初始化UI
        self.init_ui()
        
        # 设置任务队列
        self.setup_task_queue()
        
        # 创建定时器检查待处理任务
        self.task_check_timer = QTimer(self)
        self.task_check_timer.timeout.connect(self.check_for_pending_tasks)
        self.task_check_timer.start(60000)  # 每分钟检查一次
        
        # 首次检查待处理任务
        QTimer.singleShot(5000, self.check_for_pending_tasks)
        
    def init_ui(self):
        """初始化主窗口UI"""
        # 设置窗口标题和大小
        self.setWindowTitle("自动运维平台")
        self.setGeometry(100, 50, 1400, 900)  # 调整窗口大小
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主分割器，允许用户调整导航面板和内容区域的比例
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # 创建水平布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建左侧导航面板
        self.nav_panel = QWidget()
        self.nav_panel.setObjectName("navPanel")
        self.nav_panel.setMinimumWidth(380)  # 增加最小宽度
        self.nav_panel.setMaximumWidth(600)  # 增加最大宽度
        self.nav_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.nav_panel.setStyleSheet("""
            #navPanel {
                background-color: #1e272e;
                border-right: 1px solid #2d3436;
            }
            QPushButton {
                text-align: left;
                padding: 16px 30px;  /* 增加水平内边距 */
                margin: 3px 8px;     /* 增加外边距 */
                border: none;
                border-radius: 6px;
                background-color: transparent;
                color: #dfe6e9;
                font-size: 16px;     /* 增加字体大小 */
                font-weight: normal;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #2d3436;
            }
            QPushButton:checked {
                background-color: #00a8ff;
                font-weight: bold;
            }
        """)
        
        # 创建导航面板的滚动区域，以支持更多模块
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setWidget(self.nav_panel)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 左侧导航面板布局
        self.nav_layout = QVBoxLayout(self.nav_panel)
        self.nav_layout.setContentsMargins(5, 10, 5, 10)  # 增加导航面板的内边距
        self.nav_layout.setSpacing(2)  # 设置按钮之间的间距
        self.nav_layout.addStretch()  # 添加弹性空间，使按钮靠上对齐
        
        # 创建右侧内容区域
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(25, 25, 25, 25)  # 调整内容区域边距
        content_layout.setSpacing(15)  # 设置内容区域的组件间距
        
        self.content_area = QStackedWidget()
        content_layout.addWidget(self.content_area)
        
        # 添加到分割器并调整比例
        self.main_splitter.addWidget(nav_scroll)
        self.main_splitter.addWidget(content_container)
        self.main_splitter.setStretchFactor(0, 3)  # 增加导航面板比例
        self.main_splitter.setStretchFactor(1, 7)  # 增加内容区域比例
        
        # 添加到主布局
        main_layout.addWidget(self.main_splitter)
        
        # 创建菜单栏
        self.create_menu_bar()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 文件菜单
        self.file_menu = menubar.addMenu("文件(&F)")
        self.file_menu.addAction("退出(&X)", self.close)
        
        # 工具菜单
        self.tools_menu = menubar.addMenu("工具(&T)")
        
        # 帮助菜单
        self.help_menu = menubar.addMenu("帮助(&H)")
        self.help_menu.addAction("关于(&A)", self.show_about)
        
    def show_about(self):
        """显示关于对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "关于", "自动运维平台 V1.0\n\n© 2023 版权所有")
        
    def add_module(self, name, widget):
        """添加模块到左侧导航和右侧内容区域"""
        # 创建导航按钮
        nav_button = QPushButton(name)
        nav_button.setCheckable(True)
        nav_button.setFixedHeight(50)
        
        # 添加到导航面板
        self.nav_layout.insertWidget(self.nav_layout.count()-1, nav_button)  # 在弹性空间之前插入
        
        # 添加到内容区域
        self.content_area.addWidget(widget)
        
        # 连接按钮点击信号
        index = self.content_area.count() - 1
        nav_button.clicked.connect(lambda: self.switch_module(index, nav_button))
        
        # 如果是第一个模块，默认选中
        if index == 0:
            nav_button.setChecked(True)
            
    def switch_module(self, index, button):
        """切换模块显示"""
        # 取消所有按钮的选中状态
        for i in range(self.nav_layout.count()):
            item = self.nav_layout.itemAt(i)
            if item and item.widget():
                if isinstance(item.widget(), QPushButton):
                    item.widget().setChecked(False)
        
        # 设置当前按钮为选中状态
        button.setChecked(True)
        
        # 切换内容区域
        self.content_area.setCurrentIndex(index)

    def setup_task_queue(self):
        """设置任务队列和处理程序"""
        try:
            # 尝试使用基于数据库的任务队列
            from core.business.db_task_queue import get_db_task_queue
            
            # 创建任务队列实例
            self.task_queue = get_db_task_queue()
            print("已初始化基于数据库的任务队列")
            
            # 连接任务通知信号
            self.task_queue.task_added.connect(self.on_task_added)
            self.task_queue.task_status_changed.connect(self.on_task_status_changed)
            
            # 启动任务处理
            self.task_queue.start_processing()
            
            # 注册任务处理程序
            self.register_task_handlers()
            
            # 将任务队列传递给Flask应用（为了兼容性保留）
            if hasattr(self, 'flask_app'):
                from api.app import set_task_queue
                set_task_queue(self.task_queue)
                
            return True
        
        except ImportError:
            # 如果无法导入基于数据库的任务队列，则回退到使用内存任务队列
            print("警告: 无法加载基于数据库的任务队列，回退到使用内存任务队列")
            from core.business.task_queue import TaskQueue
            
            # 创建任务队列实例
            self.task_queue = TaskQueue()
            
            # 连接任务通知信号
            self.task_queue.task_added.connect(self.on_task_added)
            
            # 启动任务处理
            self.task_queue.start_processing()
            
            # 注册任务处理程序
            self.register_task_handlers()
            
            # 将任务队列传递给Flask应用
            if hasattr(self, 'flask_app'):
                from api.app import set_task_queue
                set_task_queue(self.task_queue)
                
            return False
            
    def on_task_added(self, task):
        """任务添加时的回调"""
        print(f"收到新任务通知: {task.task_id} (类型: {task.task_type})")
        # 刷新任务列表或显示通知
        self.check_for_pending_tasks()
        
    def on_task_status_changed(self, task, old_status, new_status):
        """任务状态变化的回调"""
        print(f"任务状态变化: {task.task_id} 从 {old_status} 变为 {new_status}")
        # 可以更新UI或显示通知

    def register_task_handlers(self):
        """注册任务处理程序"""
        # 注册DHCP配置任务处理程序
        self.task_queue.register_handler("dhcp_config", self.handle_dhcp_config)
        
        # 可以在这里注册其他任务处理程序...

    def handle_dhcp_config(self, params):
        """
        处理DHCP配置任务
        
        此函数兼容DBTaskQueue的处理程序格式，只接收params参数
        真正的任务执行发生在任务管理器中，这里只进行状态检查
        
        Args:
            params: 任务参数
        
        Returns:
            任务结果
        """
        print(f"MainWindow.handle_dhcp_config接收到参数: {type(params)}")
        
        # 如果参数为None，返回通用错误
        if not params:
            print("DHCP配置任务参数为空")
            return {
                'status': 'failed',
                'error': '任务参数为空'
            }
            
        # 如果是字典并包含状态字段，直接处理
        if isinstance(params, dict) and 'status' in params:
            status = params.get('status', '')
            if status == 'pending_approval':
                return {
                    'status': 'pending_approval',
                    'message': '任务正在等待管理员审核'
                }
            elif status == 'approved':
                return {
                    'status': 'approved',
                    'message': '任务已审核并处理'
                }
                
        # 对于所有其他情况，标记为待审核状态
        print(f"将任务标记为待审核状态: {params}")
        return {
            'status': 'pending_approval',
            'message': '任务已添加到审核队列'
        }
        
    def check_for_pending_tasks(self):
        """检查是否有待处理的任务"""
        # 如果未初始化任务队列，则不检查
        if not hasattr(self, 'task_queue'):
            return
        
        try:
            # 获取所有任务
            tasks = self.task_queue.get_all_tasks()
            
            if not tasks:
                return
                
            # 检查是否有待审核的任务
            pending_approval_tasks = [task for task in tasks if task.status == "pending_approval"]
            new_tasks = [task for task in tasks if task.status == "pending"]
            
            notification_msg = ""
            
            if pending_approval_tasks:
                notification_msg += f"有 {len(pending_approval_tasks)} 个待审核的任务\n"
                
            if new_tasks:
                notification_msg += f"有 {len(new_tasks)} 个新添加的任务\n"
                
            if notification_msg:
                # 有待处理任务，显示通知
                from PyQt5.QtWidgets import QMessageBox
                
                reply = QMessageBox.information(
                    self,
                    "任务通知",
                    f"{notification_msg}是否打开任务审批界面？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # 打开任务审批界面
                    self.open_approval_window()
        except Exception as e:
            print(f"检查待处理任务时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def open_approval_window(self):
        """打开任务审批窗口"""
        try:
            # 导入审批窗口类
            from modules.final_approval.gui import ApprovalWindow
            
            # 创建审批窗口
            approval_window = ApprovalWindow()
            
            # 显示窗口
            approval_window.show()
            
            # 保存窗口引用，防止被垃圾回收
            if not hasattr(self, '_approval_windows'):
                self._approval_windows = []
            self._approval_windows.append(approval_window)
            
            print("已打开任务审批窗口")
            return approval_window
            
        except Exception as e:
            print(f"打开任务审批窗口失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 显示错误消息
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "错误",
                f"打开任务审批窗口失败: {str(e)}",
                QMessageBox.Ok
            )
            return None