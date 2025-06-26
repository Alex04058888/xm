/**
 * WebSocket状态管理
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp: number;
}

interface TaskUpdate {
  task_id: number;
  status: string;
  progress?: number;
  current_node?: number;
  message?: string;
  error?: string;
  result?: any;
  log?: any;
}

interface WebSocketState {
  connection: WebSocket | null;
  isConnected: boolean;
  connectionId: string | null;
  messages: WebSocketMessage[];
  taskUpdates: Record<number, TaskUpdate[]>;
  subscriptions: Set<number>;
}

const initialState: WebSocketState = {
  connection: null,
  isConnected: false,
  connectionId: null,
  messages: [],
  taskUpdates: {},
  subscriptions: new Set(),
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setConnection: (state, action: PayloadAction<WebSocket | null>) => {
      state.connection = action.payload;
      state.isConnected = !!action.payload;
      if (!action.payload) {
        state.connectionId = null;
        state.subscriptions = new Set();
      }
    },
    setConnectionId: (state, action: PayloadAction<string>) => {
      state.connectionId = action.payload;
    },
    addMessage: (state, action: PayloadAction<WebSocketMessage>) => {
      state.messages.push(action.payload);
      // 只保留最近100条消息
      if (state.messages.length > 100) {
        state.messages = state.messages.slice(-100);
      }
    },
    addTaskUpdate: (state, action: PayloadAction<{ taskId: number; update: TaskUpdate }>) => {
      const { taskId, update } = action.payload;
      if (!state.taskUpdates[taskId]) {
        state.taskUpdates[taskId] = [];
      }
      state.taskUpdates[taskId].push(update);
      // 只保留最近50条更新
      if (state.taskUpdates[taskId].length > 50) {
        state.taskUpdates[taskId] = state.taskUpdates[taskId].slice(-50);
      }
    },
    addSubscription: (state, action: PayloadAction<number>) => {
      state.subscriptions.add(action.payload);
    },
    removeSubscription: (state, action: PayloadAction<number>) => {
      state.subscriptions.delete(action.payload);
    },
    clearMessages: (state) => {
      state.messages = [];
    },
    clearTaskUpdates: (state, action: PayloadAction<number>) => {
      delete state.taskUpdates[action.payload];
    },
  },
});

export const {
  setConnection,
  setConnectionId,
  addMessage,
  addTaskUpdate,
  addSubscription,
  removeSubscription,
  clearMessages,
  clearTaskUpdates,
} = websocketSlice.actions;

export default websocketSlice.reducer;
