import { create } from 'zustand';

interface UserInterfaceState {
  currentSidebarTab: string;
  setSidebarTab: (tab: string) => void;
  chatHistory: any[];
  addChatHistory: (messages: any[]) => void;
  addMessage: (message: any) => void;
  clearChatHistory: () => void;
  toggleSidebar: () => void;
}

export const useStore = create<UserInterfaceState>((set) => ({
  currentSidebarTab: 'search',
  setSidebarTab: (tab) => set({ currentSidebarTab: tab }),
  chatHistory: [],
  addChatHistory: (messages) => set((state) => ({ chatHistory: [...state.chatHistory, ...messages] })),
  addMessage: (message) => set((state) => ({ chatHistory: [...state.chatHistory, message] })),
  clearChatHistory: () => set({ chatHistory: [] }),
  toggleSidebar: () => {},
}));
