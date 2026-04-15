import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface SidebarState {
  collapsed: boolean;
  mobileOpen: boolean;
  expandedGroups: Record<string, boolean>;
  toggle: () => void;
  setMobileOpen: (open: boolean) => void;
  toggleGroup: (key: string) => void;
  setGroupExpanded: (key: string, expanded: boolean) => void;
}

// Grupos colapsables que arrancan abiertos por default.
const DEFAULT_EXPANDED_GROUPS: Record<string, boolean> = {
  social: false,
  aceptacion: true,
  territorio: false,
  sistema: false,
};

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      collapsed: false,
      mobileOpen: false,
      expandedGroups: DEFAULT_EXPANDED_GROUPS,
      toggle: () => set((state) => ({ collapsed: !state.collapsed })),
      setMobileOpen: (open) => set({ mobileOpen: open }),
      toggleGroup: (key) =>
        set((state) => ({
          expandedGroups: {
            ...state.expandedGroups,
            [key]: !state.expandedGroups[key],
          },
        })),
      setGroupExpanded: (key, expanded) =>
        set((state) => ({
          expandedGroups: { ...state.expandedGroups, [key]: expanded },
        })),
    }),
    {
      name: "crece_sidebar",
      storage: createJSONStorage(() => localStorage),
      // mobileOpen NO se persiste — es estado efímero de navegación.
      partialize: (state) => ({
        collapsed: state.collapsed,
        expandedGroups: state.expandedGroups,
      }),
    }
  )
);

interface ElectoralMapState {
  selectedSeccion: string | null;
  activeLayer: "intencion" | "coverage" | "penetration";
  setSelectedSeccion: (id: string | null) => void;
  setActiveLayer: (layer: "intencion" | "coverage" | "penetration") => void;
}

export const useElectoralMapStore = create<ElectoralMapState>((set) => ({
  selectedSeccion: null,
  activeLayer: "intencion",
  setSelectedSeccion: (id) => set({ selectedSeccion: id }),
  setActiveLayer: (layer) => set({ activeLayer: layer }),
}));
