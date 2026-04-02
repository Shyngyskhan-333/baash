import { create } from 'zustand';

interface UserInterfaceState {
  currentSidebarTab: string;
  setSidebarTab: (tab: string) => void;
  chatHistory: any[];
  addChatHistory: (messages: any[]) => void;
  addMessage: (message: any) => void;
  clearChatHistory: () => void;
  toggleSidebar: () => void;
  pendingMessage: string | null;
  setPendingMessage: (msg: string | null) => void;
  activeScope: string[];
  setActiveScope: (scope: string[]) => void;
  analysisResult: any | null;
  setAnalysisResult: (result: any) => void;
  selectedDocId: string | null;
  setSelectedDocId: (id: string | null) => void;
  // Search State
  searchQuery: string;
  searchResults: any[];
  searchPreview: any | null;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: any[]) => void;
  setSearchPreview: (preview: any | null) => void;
  setSearchState: (query: string, results: any[], preview: any | null) => void;
  // Audit State
  auditResults: any | null;
  auditLoading: boolean;
  setAuditResults: (results: any) => void;
  setAuditLoading: (loading: boolean) => void;
  // Diff State
  diffState: {
    textA: string;
    textB: string;
    result: any | null;
    mode: 'split' | 'unified';
  };
  setDiffState: (state: Partial<UserInterfaceState['diffState']>) => void;
  // Graph State
  graphState: {
    activeTab: 'graph' | 'heatmap';
    filterType: string;
    plotData: any | null;
    plotLayout: any | null;
  };
  setGraphState: (state: Partial<UserInterfaceState['graphState']>) => void;
}

export const useStore = create<UserInterfaceState>((set) => ({
  currentSidebarTab: 'search',
  setSidebarTab: (tab) => set({ currentSidebarTab: tab }),
  chatHistory: [],
  addChatHistory: (messages) => set((state) => ({ chatHistory: [...state.chatHistory, ...messages] })),
  addMessage: (message) => set((state) => ({ chatHistory: [...state.chatHistory, message] })),
  clearChatHistory: () => set({ chatHistory: [] }),
  toggleSidebar: () => {},
  pendingMessage: null,
  setPendingMessage: (msg) => set({ pendingMessage: msg }),
  activeScope: [],
  setActiveScope: (scope) => set({ activeScope: scope }),
  analysisResult: null,
  setAnalysisResult: (result) => set({ analysisResult: result }),
  selectedDocId: null,
  setSelectedDocId: (id) => set({ selectedDocId: id }),
  // Search
  searchQuery: '',
  searchResults: [],
  searchPreview: null,
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),
  setSearchPreview: (preview) => set({ searchPreview: preview }),
  setSearchState: (query, results, preview) => set({ searchQuery: query, searchResults: results, searchPreview: preview }),
  // Audit
  auditResults: null,
  auditLoading: false,
  setAuditResults: (results) => set({ auditResults: results }),
  setAuditLoading: (loading) => set({ auditLoading: loading }),
  // Diff
  diffState: {
    textA: '',
    textB: '',
    result: null,
    mode: 'split',
  },
  setDiffState: (partial) => set((state) => ({ 
    diffState: { ...state.diffState, ...partial } 
  })),
  // Graph
  graphState: {
    activeTab: 'graph',
    filterType: 'Все',
    plotData: null,
    plotLayout: null,
  },
  setGraphState: (partial) => set((state) => ({ 
    graphState: { ...state.graphState, ...partial } 
  })),
}));
