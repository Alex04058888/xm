/**
 * Redux Store配置
 */
import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import profileSlice from './slices/profileSlice';
import rpaSlice from './slices/rpaSlice';
import taskSlice from './slices/taskSlice';
import websocketSlice from './slices/websocketSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    profiles: profileSlice,
    rpa: rpaSlice,
    tasks: taskSlice,
    websocket: websocketSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['websocket/setConnection'],
        ignoredPaths: ['websocket.connection'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
