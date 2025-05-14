// 文档加载完成后执行
$(document).ready(function() {
    console.log("应用已加载");
    
    // 初始化所有提示工具
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化所有弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 初始化数据表格
    if ($.fn.DataTable) {
        $('.datatable').DataTable({
            language: {
                url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/zh.json"
            }
        });
    }
    
    // 侧边栏切换
    $('.sidebar-toggle').on('click', function() {
        $('.sidebar').toggleClass('show');
    });
    
    // AJAX请求设置
    $.ajaxSetup({
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        error: function(xhr, status, error) {
            // 错误处理
            console.error("AJAX错误: " + status + " " + error);
            toastr.error("请求失败: " + error);
        }
    });
    
    // 通知设置
    if (typeof toastr !== 'undefined') {
        toastr.options = {
            closeButton: true,
            progressBar: true,
            positionClass: "toast-top-right",
            timeOut: 5000
        };
    }
    
    // 设置WebSocket连接状态指示器
    var wsStatusElement = $('#ws-status');
    if (wsStatusElement.length) {
        // 尝试连接SocketIO
        if (typeof io !== 'undefined') {
            var socket = io();
            
            // 连接成功
            socket.on('connect', function() {
                wsStatusElement.html('<span class="badge bg-success">已连接</span>');
                console.log('SocketIO连接成功');
            });
            
            // 连接断开
            socket.on('disconnect', function() {
                wsStatusElement.html('<span class="badge bg-danger">已断开</span>');
                console.log('SocketIO连接断开');
            });
            
            // 接收设备状态更新
            socket.on('device_status_update', function(data) {
                console.log('收到设备状态更新', data);
                updateDeviceStatusUI(data);
            });
            
            // 接收任务状态更新
            socket.on('task_status_update', function(data) {
                console.log('收到任务状态更新', data);
                updateTaskStatusUI(data);
            });
        } else {
            wsStatusElement.html('<span class="badge bg-warning">未启用</span>');
            console.log('SocketIO库未加载');
        }
    }
    
    // DHCP表单提交
    $('#dhcp-form').on('submit', function(e) {
        e.preventDefault();
        
        var formData = {
            device_ids: $('#device_ids').val(),
            pool_name: $('#pool_name').val(),
            network: $('#network').val(),
            mask: $('#mask').val(),
            gateway: $('#gateway').val(),
            dns: $('#dns').val(),
            domain: $('#domain').val(),
            lease_days: $('#lease_days').val()
        };
        
        // 显示加载状态
        $('#submit-btn').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 提交中...');
        
        // 发送AJAX请求
        $.ajax({
            url: '/dhcp/submit',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                // 恢复按钮状态
                $('#submit-btn').prop('disabled', false).html('提交配置');
                
                // 显示成功消息
                toastr.success('DHCP配置任务已提交，任务ID: ' + response.task_id);
                
                // 清空表单
                $('#dhcp-form')[0].reset();
            },
            error: function(xhr, status, error) {
                // 恢复按钮状态
                $('#submit-btn').prop('disabled', false).html('提交配置');
                
                // 显示错误消息
                var errorMsg = '提交失败';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                toastr.error(errorMsg);
            }
        });
    });
    
    // 更新设备状态UI
    function updateDeviceStatusUI(data) {
        // 如果页面上有设备状态容器
        if ($('#device-status-container').length) {
            // 更新统计数字
            if (data.summary) {
                $('#online-count').text(data.summary.online || 0);
                $('#offline-count').text(data.summary.offline || 0);
                $('#unknown-count').text(data.summary.unknown || 0);
                $('#total-devices').text(data.summary.total || 0);
            }
            
            // 如果有设备列表表格并且提供了设备数据
            if ($('#devices-table').length && data.devices) {
                var table = $('#devices-table').DataTable();
                
                // 清空表格
                table.clear();
                
                // 添加新数据
                data.devices.forEach(function(device) {
                    var statusClass = '';
                    if (device.status === 'online') {
                        statusClass = 'bg-success';
                    } else if (device.status === 'offline') {
                        statusClass = 'bg-danger';
                    } else {
                        statusClass = 'bg-warning';
                    }
                    
                    table.row.add([
                        device.id,
                        device.name,
                        device.ip_address,
                        '<span class="badge ' + statusClass + '">' + device.status + '</span>',
                        device.last_checked || '-'
                    ]);
                });
                
                // 重绘表格
                table.draw();
            }
        }
    }
    
    // 更新任务状态UI
    function updateTaskStatusUI(data) {
        // 如果页面上有任务状态表格
        if ($('#tasks-table').length) {
            var taskRow = $('#task-' + data.task_id);
            
            if (taskRow.length) {
                // 更新现有行
                taskRow.find('.task-status').html('<span class="badge bg-' + getStatusBadgeClass(data.status) + '">' + data.status + '</span>');
                taskRow.find('.task-progress').text(data.progress + '%');
                taskRow.find('.progress-bar')
                    .css('width', data.progress + '%')
                    .attr('aria-valuenow', data.progress);
                
                // 如果任务完成，显示通知
                if (data.status === 'completed') {
                    toastr.success('任务 #' + data.task_id + ' 已完成');
                } else if (data.status === 'failed') {
                    toastr.error('任务 #' + data.task_id + ' 失败: ' + data.message);
                }
            } else {
                // 添加新行
                var progressBarHtml = '<div class="progress">' +
                    '<div class="progress-bar" role="progressbar" style="width: ' + data.progress + '%;" ' +
                    'aria-valuenow="' + data.progress + '" aria-valuemin="0" aria-valuemax="100">' + data.progress + '%</div>' +
                    '</div>';
                
                var newRow = '<tr id="task-' + data.task_id + '">' +
                    '<td>' + data.task_id + '</td>' +
                    '<td>' + data.type + '</td>' +
                    '<td class="task-status"><span class="badge bg-' + getStatusBadgeClass(data.status) + '">' + data.status + '</span></td>' +
                    '<td class="task-progress">' + progressBarHtml + '</td>' +
                    '<td>' + data.created_at + '</td>' +
                    '</tr>';
                
                $('#tasks-table tbody').prepend(newRow);
            }
        }
    }
    
    // 获取状态对应的Badge类
    function getStatusBadgeClass(status) {
        switch (status) {
            case 'completed':
                return 'success';
            case 'in_progress':
                return 'primary';
            case 'pending':
                return 'info';
            case 'failed':
                return 'danger';
            case 'pending_approval':
                return 'warning';
            default:
                return 'secondary';
        }
    }
}); 