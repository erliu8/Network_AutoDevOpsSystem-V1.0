# database.py
import os

# 数据库配置
DB_CONFIG = {
    'default': {
        'ENGINE': 'mysql',  # 数据库类型: mysql, postgresql, sqlite
        'NAME': 'autodevops',  # 数据库名称
        'USER': 'root',  # 数据库用户名
        'PASSWORD': '000000',  # 数据库密码
        'HOST': 'localhost',  # 数据库主机
        'PORT': '3306',  # 数据库端口
    }
}

# SQLAlchemy连接字符串
def get_connection_string():
    config = DB_CONFIG['default']
    
    if config['ENGINE'] == 'sqlite':
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return f"sqlite:///{os.path.join(base_dir, config['NAME'])}"
    
    elif config['ENGINE'] == 'mysql':
        return f"mysql+pymysql://{config['USER']}:{config['PASSWORD']}@{config['HOST']}:{config['PORT']}/{config['NAME']}"
    
    elif config['ENGINE'] == 'postgresql':
        return f"postgresql://{config['USER']}:{config['PASSWORD']}@{config['HOST']}:{config['PORT']}/{config['NAME']}"
    
    else:
        raise ValueError(f"不支持的数据库引擎: {config['ENGINE']}")

# 添加测试数据库连接函数
def test_database_connection():
    """测试数据库连接是否正常
    
    Returns:
        bool: 连接是否成功
    """
    try:
        import pymysql
        
        # 使用默认配置进行连接测试
        config = DB_CONFIG['default']
        
        # 创建连接
        connection = pymysql.connect(
            host=config['HOST'],
            port=int(config['PORT']),
            user=config['USER'],
            password=config['PASSWORD'],
            database=config['NAME'],
            charset='utf8mb4'
        )
        
        # 测试执行简单查询
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        # 关闭连接
        connection.close()
        
        print(f"[INFO] 数据库连接测试成功: {config['HOST']}:{config['PORT']}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 数据库连接测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False