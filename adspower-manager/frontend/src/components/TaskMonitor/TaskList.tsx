/**
 * 任务列表组件
 */
import React, { useState, useEffect } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Progress,
  Tooltip,
  Modal,
  message,
  Dropdown,
  Menu,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  RedoOutlined,
  DeleteOutlined,
  EyeOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { Task } from '@/types/api';
import { taskService } from '@/services/taskService';
import { useWebSocket } from '@/hooks/useWebSocket';
import { formatDateTime, formatDuration } from '@/utils/dateUtils';
import TaskLogModal from './TaskLogModal';

interface TaskListProps {
  tasks: Task[];
  loading: boolean;
  onRefresh: () => void;
  onTaskUpdate: (task: Task) => void;
}

const TaskList: React.FC<TaskListProps> = ({
  tasks,
  loading,
  onRefresh,
  onTaskUpdate,
}) => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [logModalVisible, setLogModalVisible] = useState(false);
  const { subscribeToTask, unsubscribeFromTask, subscriptions } = useWebSocket();

  // 状态标签配置
  const statusConfig = {
    pending: { color: 'default', text: '等待中' },
    running: { color: 'processing', text: '执行中' },
    completed: { color: 'success', text: '已完成' },
    failed: { color: 'error', text: '失败' },
    cancelled: { color: 'warning', text: '已取消' },
    paused: { color: 'warning', text: '已暂停' },
  };

  const getStatusTag = (status: string) => {
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const handleExecuteTask = async (taskId: number) => {
    try {
      await taskService.executeTask(taskId);
      message.success('任务开始执行');
      subscribeToTask(taskId);
      onRefresh();
    } catch (error) {
      message.error('启动任务失败');
    }
  };

  const handleCancelTask = async (taskId: number) => {
    try {
      await taskService.cancelTask(taskId);
      message.success('任务已取消');
      unsubscribeFromTask(taskId);
      onRefresh();
    } catch (error) {
      message.error('取消任务失败');
    }
  };

  const handleRetryTask = async (taskId: number) => {
    try {
      await taskService.retryTask(taskId);
      message.success('任务重试中');
      subscribeToTask(taskId);
      onRefresh();
    } catch (error) {
      message.error('重试任务失败');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个任务吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await taskService.deleteTask(taskId);
          message.success('任务已删除');
          unsubscribeFromTask(taskId);
          onRefresh();
        } catch (error) {
          message.error('删除任务失败');
        }
      },
    });
  };

  const handleViewLogs = (task: Task) => {
    setSelectedTask(task);
    setLogModalVisible(true);
  };

  const getActionMenu = (task: Task) => (
    <Menu>
      {task.status === 'pending' && (
        <Menu.Item
          key="execute"
          icon={<PlayCircleOutlined />}
          onClick={() => handleExecuteTask(task.id)}
        >
          执行任务
        </Menu.Item>
      )}
      {task.status === 'running' && (
        <Menu.Item
          key="cancel"
          icon={<PauseCircleOutlined />}
          onClick={() => handleCancelTask(task.id)}
        >
          取消任务
        </Menu.Item>
      )}
      {task.status === 'failed' && (
        <Menu.Item
          key="retry"
          icon={<RedoOutlined />}
          onClick={() => handleRetryTask(task.id)}
        >
          重试任务
        </Menu.Item>
      )}
      <Menu.Item
        key="logs"
        icon={<EyeOutlined />}
        onClick={() => handleViewLogs(task)}
      >
        查看日志
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item
        key="delete"
        icon={<DeleteOutlined />}
        danger
        onClick={() => handleDeleteTask(task.id)}
      >
        删除任务
      </Menu.Item>
    </Menu>
  );

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a: Task, b: Task) => a.id - b.id,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: Task) => (
        <Tooltip title={record.description}>
          <span>{name || `任务 ${record.id}`}</span>
        </Tooltip>
      ),
    },
    {
      title: '环境',
      dataIndex: 'profile_name',
      key: 'profile_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'RPA流程',
      dataIndex: 'rpa_flow_name',
      key: 'rpa_flow_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
      filters: Object.entries(statusConfig).map(([key, config]) => ({
        text: config.text,
        value: key,
      })),
      onFilter: (value: string, record: Task) => record.status === value,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number, record: Task) => (
        <div>
          <Progress
            percent={progress}
            size="small"
            status={record.status === 'failed' ? 'exception' : undefined}
          />
          {subscriptions.includes(record.id) && (
            <Tag color="blue" size="small" style={{ marginTop: 4 }}>
              实时监控
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a: Task, b: Task) => a.priority - b.priority,
      render: (priority: number) => (
        <Tag color={priority >= 8 ? 'red' : priority >= 5 ? 'orange' : 'default'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time: string) => formatDateTime(time),
      sorter: (a: Task, b: Task) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '执行时长',
      key: 'duration',
      width: 100,
      render: (_, record: Task) => {
        if (record.duration) {
          return formatDuration(record.duration);
        }
        if (record.started_at && !record.completed_at) {
          const duration = (Date.now() - new Date(record.started_at).getTime()) / 1000;
          return formatDuration(duration);
        }
        return '-';
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      fixed: 'right' as const,
      render: (_, record: Task) => (
        <Dropdown overlay={getActionMenu(record)} trigger={['click']}>
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  return (
    <>
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        pagination={{
          total: tasks.length,
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
        scroll={{ x: 1200 }}
        size="small"
      />

      <TaskLogModal
        visible={logModalVisible}
        task={selectedTask}
        onClose={() => {
          setLogModalVisible(false);
          setSelectedTask(null);
        }}
      />
    </>
  );
};

export default TaskList;
