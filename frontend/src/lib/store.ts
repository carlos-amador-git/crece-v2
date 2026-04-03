import { create } from "zustand";

interface SidebarState {
  collapsed: boolean;
  mobileOpen: boolean;
  toggle: () => void;
  setMobileOpen: (open: boolean) => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  collapsed: false,
  mobileOpen: false,
  toggle: () => set((state) => ({ collapsed: !state.collapsed })),
  setMobileOpen: (open) => set({ mobileOpen: open }),
}));

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
