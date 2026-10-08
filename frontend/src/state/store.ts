"use client";

import { useSyncExternalStore } from "react";
import type { ProfileAnswers, TxInput } from "@/engine/types";
import { seedHistory } from "./seed";

export interface User {
  id: string;
  alias: string;
  createdAt: number;
  answers: ProfileAnswers;
}

export interface HistoryEntry {
  id: string;
  userId: string;
  createdAt: number;
  tx: TxInput;
  /** Profile at the time of the analysis, so the result is reproducible. */
  answers: ProfileAnswers;
  seeded?: boolean;
}

export interface StoreState {
  users: User[];
  activeId: string | null;
  history: HistoryEntry[];
  draft: TxInput | null;
}

const KEY = "redfacil.demo.v2";
const EMPTY: StoreState = { users: [], activeId: null, history: [], draft: null };

let state: StoreState = EMPTY;
let loaded = false;
const listeners = new Set<() => void>();

function load() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) state = { ...EMPTY, ...(JSON.parse(raw) as Partial<StoreState>) };
  } catch {
    state = EMPTY;
  }
}

function commit(next: StoreState) {
  state = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Storage may be unavailable (private mode); the app keeps working in memory.
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const getSnapshot = () => {
  load();
  return state;
};
const getServerSnapshot = () => EMPTY;

export function useStore(): StoreState {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** False during server render and hydration, true afterwards. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

export function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export const actions = {
  createUser(alias: string, answers: ProfileAnswers): string {
    load();
    const user: User = { id: newId(), alias, createdAt: Date.now(), answers };
    const history = seedHistory(user, newId);
    commit({
      ...state,
      users: [...state.users, user],
      activeId: user.id,
      history: [...state.history, ...history],
    });
    return user.id;
  },
  updateUser(id: string, alias: string, answers: ProfileAnswers) {
    load();
    commit({
      ...state,
      users: state.users.map((u) => (u.id === id ? { ...u, alias, answers } : u)),
    });
  },
  deleteUser(id: string) {
    load();
    const users = state.users.filter((u) => u.id !== id);
    commit({
      ...state,
      users,
      activeId: state.activeId === id ? (users[0]?.id ?? null) : state.activeId,
      history: state.history.filter((h) => h.userId !== id),
    });
  },
  setActive(id: string | null) {
    load();
    commit({ ...state, activeId: id });
  },
  setDraft(tx: TxInput | null) {
    load();
    commit({ ...state, draft: tx });
  },
  addHistory(tx: TxInput): string | null {
    load();
    const user = state.users.find((u) => u.id === state.activeId);
    if (!user) return null;
    const entry: HistoryEntry = {
      id: newId(),
      userId: user.id,
      createdAt: Date.now(),
      tx,
      answers: user.answers,
    };
    commit({ ...state, history: [...state.history, entry], draft: null });
    return entry.id;
  },
  clearHistory(userId: string) {
    load();
    commit({ ...state, history: state.history.filter((h) => h.userId !== userId) });
  },
};

export function useActiveUser(): User | null {
  const s = useStore();
  return s.users.find((u) => u.id === s.activeId) ?? null;
}
