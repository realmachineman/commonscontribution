import publicConfig from '../config/dynamic.public.json';

export const dynamicEnvironmentId = String(
  import.meta.env.VITE_DYNAMIC_ENVIRONMENT_ID || publicConfig.environmentId || ''
).trim();

export function shortenWallet(address) {
  if (!address) return '';
  return address.slice(0, 6) + '…' + address.slice(-4);
}
