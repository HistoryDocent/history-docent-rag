/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HISTORY_DOCENT_CHAT_MODE?: "fixture" | "backend";
  readonly VITE_HISTORY_DOCENT_API_BASE_URL?: string;
}
