import { createClient } from '@supabase/supabase-js';

export let supabase = null;
export let authSetupError = '';
export async function initializeAuth() {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw new Error('Could not load account configuration.');
    const config = await response.json();
    const url = config.supabaseUrl || import.meta.env.VITE_SUPABASE_URL;
    const key = config.supabasePublishableKey || import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
    if (!url || !key) {
      authSetupError = 'Account registration will open once the community’s Supabase project is connected.';
      return;
    }
    supabase = createClient(url, key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit' },
    });
    // Capture recovery before the initial session is consumed, including provider fallback redirects.
    const recovery=new URLSearchParams(location.hash.slice(1)).get('type')==='recovery';
    await supabase.auth.getSession();
    if(recovery)history.replaceState(null,'','/auth/reset');
  } catch (error) { authSetupError = error.message; }
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
