import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export interface ChatSource {
  article: string;
}

export interface ChatMessage {
  role: string;
  content: string;
  sources?: ChatSource[];
}

export interface SearchResultItem {
  doc_id: string;
  title: string;
  excerpt?: string;
  text?: string;
  score?: number;
  bm25_score?: number;
  cosine_score?: number;
}

export interface SearchPreviewItem {
  doc_id: string;
  title: string;
  date?: string;
  versions_found: number;
  versions: { version_id: string; date: string; status: string }[];
}

export interface AnalysisIssue {
  article: string;
  severity: string;
  type: string;
  description: string;
  explanation?: string;
  related_doc_id?: string;
  signals?: Record<string, unknown>;
}

export interface AnalysisRelatedLaw {
  doc_id: string;
  title: string;
  relevance_score?: number;
}

export interface AnalysisResult {
  doc_id: string;
  title: string;
  risk_score: number;
  risk_level: string;
  summary: string;
  summary_short?: string;
  sections?: Record<string, string>;
  reasoning?: string;
  issues: AnalysisIssue[];
  related_laws?: AnalysisRelatedLaw[];
}

export interface AuditResults {
  status: string;
  stats: Record<string, number>;
  contradictions: Array<Record<string, unknown>>;
  duplicates: Array<Record<string, unknown>>;
  outdated: Array<Record<string, unknown>>;
}

export interface DiffResult {
  hunks: Array<{ type: string; line_number: number; old_text?: string; new_text?: string }>;
  stats: { added: number; removed: number; changed: number };
  ai_summary: string;
}

interface UserInterfaceState {
  currentSidebarTab: string;
  setSidebarTab: (tab: string) => void;
  chatHistory: ChatMessage[];
  addChatHistory: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  clearChatHistory: () => void;
  toggleSidebar: () => void;
  pendingMessage: string | null;
  setPendingMessage: (msg: string | null) => void;
  activeScope: string[];
  setActiveScope: (scope: string[]) => void;
  analysisResult: AnalysisResult | null;
  setAnalysisResult: (result: AnalysisResult | null) => void;
  selectedDocId: string | null;
  setSelectedDocId: (id: string | null) => void;
  searchQuery: string;
  searchResults: SearchResultItem[];
  searchPreview: SearchPreviewItem | null;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: SearchResultItem[]) => void;
  setSearchPreview: (preview: SearchPreviewItem | null) => void;
  setSearchState: (query: string, results: SearchResultItem[], preview: SearchPreviewItem | null) => void;
  auditResults: AuditResults | null;
  auditLoading: boolean;
  setAuditResults: (results: AuditResults | null) => void;
  setAuditLoading: (loading: boolean) => void;
  diffState: {
    textA: string;
    textB: string;
    result: DiffResult | null;
    mode: 'split' | 'unified';
    hideUnchanged: boolean;
    showKeywords: boolean;
  };
  setDiffState: (state: Partial<UserInterfaceState['diffState']>) => void;
  graphState: {
    activeTab: 'graph' | 'heatmap';
    filterType: string;
    plotData: Array<Record<string, unknown>> | null;
    plotLayout: Record<string, unknown> | null;
  };
  setGraphState: (state: Partial<UserInterfaceState['graphState']>) => void;
}

export const useStore = create<UserInterfaceState>()(
  persist(
    (set) => ({
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
      searchQuery: '',
      searchResults: [],
      searchPreview: null,
      setSearchQuery: (query) => set({ searchQuery: query }),
      setSearchResults: (results) => set({ searchResults: results }),
      setSearchPreview: (preview) => set({ searchPreview: preview }),
      setSearchState: (query, results, preview) =>
        set({ searchQuery: query, searchResults: results, searchPreview: preview }),
      auditResults: null,
      auditLoading: false,
      setAuditResults: (results) => set({ auditResults: results }),
      setAuditLoading: (loading) => set({ auditLoading: loading }),
      diffState: {
        textA: '',
        textB: '',
        result: null,
        mode: 'split',
        hideUnchanged: true,
        showKeywords: true,
      },
      setDiffState: (partial) =>
        set((state) => ({
          diffState: { ...state.diffState, ...partial },
        })),
      graphState: {
        activeTab: 'graph',
        filterType: '\u0412\u0441\u0435',
        plotData: null,
        plotLayout: null,
      },
      setGraphState: (partial) =>
        set((state) => ({
          graphState: { ...state.graphState, ...partial },
        })),
    }),
    {
      name: 'legal-entropy-ui-state',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        chatHistory: state.chatHistory.slice(-20),
        activeScope: state.activeScope,
        selectedDocId: state.selectedDocId,
        auditResults: null,
        diffState: {
          ...state.diffState,
          textA: '',
          textB: '',
          result: null,
        },
        graphState: {
          activeTab: state.graphState.activeTab,
          filterType: state.graphState.filterType,
          plotData: null,
          plotLayout: null,
        },
      }),
    }
  )
);