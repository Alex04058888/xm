/**
 * WebSocket Hook
 */
import { useEffect, useCallback, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { message } from 'antd';
import { RootState } from '@/store';
import {
  setConnection,
  setConnectionId,
  addMessage,
  addTaskUpdate,
  addSubscription,
  removeSubscription,
} from '@/store/slices/websocketSlice';

export const useWebSocket = () => {
  const dispatch = useDispatch();
  const { connection, isConnected, connectionId, subscriptions } = useSelector(
    (state: RootState) => state.websocket
  );
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!isAuthenticated) {
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      return;
    }

    try {
      const wsUrl = `${process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000'}/api/v1/ws?token=${token}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        dispatch(setConnection(ws));
        reconnectAttemptsRef.current = 0;
        message.success('实时连接已建立');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);

          // 添加到消息历史
          dispatch(addMessage({
            type: data.type,
            data: data,
            timestamp: Date.now(),
          }));

          // 处理不同类型的消息
          switch (data.type) {
            case 'welcome':
              dispatch(setConnectionId(data.connection_id));
              break;

            case 'task_update':
              dispatch(addTaskUpdate({
                taskId: data.task_id,
                update: {
                  task_id: data.task_id,
                  status: data.data.status,
                  progress: data.data.progress,
                  current_node: data.data.current_node,
                  message: data.data.message,
                  error: data.data.error,
                  result: data.data.result,
                  log: data.data.log,
                },
              }));

              // 显示任务状态通知
              if (data.data.status === 'completed') {
                message.success(`任务 ${data.task_id} 执行完成`);
              } else if (data.data.status === 'failed') {
                message.error(`任务 ${data.task_id} 执行失败: ${data.data.error}`);
              }
              break;

            case 'system_notification':
              message.info(data.data.message);
              break;

            case 'error':
              message.error(data.message);
              break;

            default:
              console.log('Unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        dispatch(setConnection(null));

        // 自动重连
        if (isAuthenticated && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000; // 指数退避
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          message.error('WebSocket连接失败，请刷新页面重试');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        message.error('WebSocket连接错误');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      message.error('无法建立WebSocket连接');
    }
  }, [isAuthenticated, dispatch]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (connection) {
      connection.close();
      dispatch(setConnection(null));
    }
  }, [connection, dispatch]);

  const sendMessage = useCallback((message: any) => {
    if (connection && connection.readyState === WebSocket.OPEN) {
      connection.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, [connection]);

  const subscribeToTask = useCallback((taskId: number) => {
    if (sendMessage({ type: 'subscribe_task', task_id: taskId })) {
      dispatch(addSubscription(taskId));
      return true;
    }
    return false;
  }, [sendMessage, dispatch]);

  const unsubscribeFromTask = useCallback((taskId: number) => {
    if (sendMessage({ type: 'unsubscribe_task', task_id: taskId })) {
      dispatch(removeSubscription(taskId));
      return true;
    }
    return false;
  }, [sendMessage, dispatch]);

  const ping = useCallback(() => {
    return sendMessage({ type: 'ping' });
  }, [sendMessage]);

  // 自动连接和断开
  useEffect(() => {
    if (isAuthenticated && !connection) {
      connect();
    } else if (!isAuthenticated && connection) {
      disconnect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isAuthenticated, connection, connect, disconnect]);

  // 定期ping保持连接
  useEffect(() => {
    if (isConnected) {
      const pingInterval = setInterval(() => {
        ping();
      }, 30000); // 每30秒ping一次

      return () => clearInterval(pingInterval);
    }
  }, [isConnected, ping]);

  return {
    isConnected,
    connectionId,
    subscriptions: Array.from(subscriptions),
    connect,
    disconnect,
    sendMessage,
    subscribeToTask,
    unsubscribeFromTask,
    ping,
  };
};
