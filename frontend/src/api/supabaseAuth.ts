import { createClient, type SupabaseClient } from "@supabase/supabase-js";
let client: SupabaseClient | null = null;
export function isSupabaseConfigured() { return Boolean(import.meta.env.VITE_SUPABASE_URL?.trim() && import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim()); }
export function supabase() { if (!client) { const url = import.meta.env.VITE_SUPABASE_URL?.trim(); const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim(); if (!url || !key) throw new Error("Supabase URL과 publishable key를 설정해 주세요."); client = createClient(url, key); } return client; }
export async function signInWithGoogle(destination: "home" | "practice" = "home") { try { sessionStorage.setItem("malhaebom-login-destination", destination); } catch (_error) {} const { error } = await supabase().auth.signInWithOAuth({ provider: "google", options: { redirectTo: window.location.origin } }); if (error) throw error; }
export async function signOut() { const { error } = await supabase().auth.signOut(); if (error) throw error; }
