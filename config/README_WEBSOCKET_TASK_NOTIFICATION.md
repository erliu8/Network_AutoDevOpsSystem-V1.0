# WebSocket 任务通知系统

## 系统概述

WebSocket 任务通知系统是为了解决 Flask Web 应用和 PyQt 桌面应用之间任务实时通知问题而设计的。该系统使用 WebSocket 协议实现了任务状态变化的即时推送，避免了轮询数据库造成的延迟和资源浪费。

## 系统架构

系统主要包含以下组件：

1. **WebSocket 服务器** - 管理客户端连接，广播任务状态变化
2. **Flask Web 应用** - 处理用户请求，执行任务，并通过 WebSocket 服务器通知状态变化
3. **PyQt 桌面应用** - 连接到 WebSocket 服务器，接收实时任务通知

### 工作流程

1. Flask Web 应用启动时会同时启动 WebSocket 服务器
2. PyQt 桌面应用启动时会连接到 WebSocket 服务器，并注册为客户端
3. 当用户提交任务时，任务会被存储到数据库
4. 任务状态变化时，Flask Web 应用会通过 WebSocket 服务器广播通知
5. PyQt 桌面应用通过 WebSocket 连接接收通知，并更新界面

## 运行方式

### 启动完整系统

使用 `start_system.bat` 脚本启动完整系统：

```
start_system.bat
```

该脚本会按照正确的顺序启动 Web 服务器、WebSocket 服务器和 PyQt 桌面应用。

### 测试 WebSocket 任务通知

使用 `start_websocket_test.bat` 脚本测试 WebSocket 任务通知：

```
start_websocket_test.bat
```

该脚本会启动 WebSocket 服务器，并运行测试脚本创建和更新任务，验证任务通知是否正常工作。

## 关键文件说明

- `run_web.py` - Flask Web 应用启动脚本，包含 WebSocket 服务器启动代码
- `run_app.py` - PyQt 桌面应用启动脚本，包含 WebSocket 客户端连接代码
- `shared/websocket/server.py` - WebSocket 服务器实现
- `shared/websocket/client.py` - WebSocket 客户端实现
- `shared/websocket/handlers.py` - WebSocket 消息处理程序
- `test_websocket_task_notification.py` - WebSocket 任务通知测试脚本

## 故障排除

### WebSocket 连接失败

如果 PyQt 应用无法连接到 WebSocket 服务器，请检查：

1. WebSocket 服务器是否已启动（默认端口为 8765）
2. 是否有防火墙或网络限制阻止 WebSocket 连接
3. 服务器地址和端口是否正确配置

### 任务通知未收到

如果任务状态更新后未收到通知，请检查：

1. WebSocket 连接是否正常（查看 PyQt 应用日志）
2. 任务状态是否已正确更新到数据库
3. 通知函数是否正确调用（查看 Web 应用日志）

## 兼容性说明

该系统保留了数据库轮询的兼容性功能，确保旧版 PyQt 应用也能正常工作。当 PyQt 应用未运行时，任务会正常存储到数据库，并在 PyQt 应用启动时同步到本地。 