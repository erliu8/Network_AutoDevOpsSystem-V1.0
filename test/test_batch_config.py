# test_batch_config.py
import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# 添加模块目录到系统路径
module_dir = str(Path(__file__).parent)
sys.path.append(module_dir)

from PyQt5.QtWidgets import QApplication
# 使用绝对导入
from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController

if __name__ == "__main__":
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建控制器
    controller = BatchConfigController()
    
    # 显示窗口
    controller.show_window()
    
    # 运行应用程序
    sys.exit(app.exec_())