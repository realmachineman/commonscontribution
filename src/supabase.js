import { createClient } from '@supabase/supabase-js';
import publicConfig from '../config/supabase.public.json';

export let supabase = null;
export let authSetupError = '';

export async function initializeAuth() {
  try {
    let url = import.meta.env.VITE_SUPABASE_URL || '';
    let key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || '';
    try {
      const response = await fetch('/api/config');
      if (response.ok && (response.headers.get('content-type') || '').includes('application/json')) {
        const config = await response.json();
        url = config.supabaseUrl || url;
        key = config.supabasePublishableKey || key;
      }
    } catch {}
    url = url || publicConfig.url;
    key = key || publicConfig.publishableKey;
    if (!url || !key) {
      authSetupError = 'Account registration will open once the community’s Supabase project is connected.';
      return;
    }
    supabase = createClient(url, key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit' },
    });
    const recovery = new URLSearchParams(location.hash.slice(1)).get('type') === 'recovery';
    await supabase.auth.getSession();
    if (recovery) history.replaceState(null, '', '/auth/reset');
  } catch (error) {
    authSetupError = error.message;
  }
}

export async function authAction(action, values = {}) {
  if (!supabase) throw new Error(authSetupError || 'Supabase is not configured.');
  let result;
  if (action === 'signup') {
    result = await supabase.auth.signUp({
      email: values.email, password: values.password,
      options: { data: { name: values.name, city: values.city }, emailRedirectTo: `${location.origin}/auth/callback` },
    });
  } else if (action === 'login') {
    result = await supabase.auth.signInWithPassword({ email: values.email, password: values.password });
  } else if (action === 'logout') {
    result = await supabase.auth.signOut({ scope: 'local' });
  } else if (action === 'reset-request') {
    result = await supabase.auth.resetPasswordForEmail(values.email, { redirectTo: `${location.origin}/auth/reset` });
  } else if (action === 'resend') {
    result = await supabase.auth.resend({ type: 'signup', email: values.email, options: { emailRedirectTo: `${location.origin}/auth/callback` } });
  } else if (action === 'password') {
    result = await supabase.auth.updateUser({ password: values.password, current_password: values.current });
  } else if (action === 'recovery') {
    result = await supabase.auth.updateUser({ password: values.password });
  } else throw new Error('Unknown account action.');
  if (result.error) throw result.error;
  return result.data || {};
}

export async function sessionProfile() {
  if (!supabase) return null;
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  const meta = user.user_metadata || {};
  return {
    id: user.id,
    name: String(meta.name || (user.email || 'Neighbor').split('@')[0]),
    email: user.email,
    city: String(meta.city || 'Not specified'),
    categories: [],
    bio: '',
    avatar: '',
    credits: 0,
    score: 0,
  };
}
