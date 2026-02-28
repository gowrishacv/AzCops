import { PublicClientApplication, Configuration, LogLevel } from '@azure/msal-browser';

const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_AZURE_CLIENT_ID ?? '',
    authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_AZURE_TENANT_ID ?? 'common'}`,
    redirectUri: process.env.NEXT_PUBLIC_AZURE_REDIRECT_URI ?? 'http://localhost:3000',
    postLogoutRedirectUri: '/',
  },
  cache: { cacheLocation: 'sessionStorage', storeAuthStateInCookie: false },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
      loggerCallback: (level, message) => {
        if (level === LogLevel.Error) console.error(message);
      },
    },
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

/** Backend API scope — e.g. api://CLIENT_ID/access_as_user */
const apiScope = process.env.NEXT_PUBLIC_AZURE_API_SCOPE ?? '';

/** Scopes for interactive login (includes openid + API) */
export const loginRequest = {
  scopes: ['openid', 'profile', 'email', ...(apiScope ? [apiScope] : [])],
};

/** Scopes for silent token acquisition (just API) */
export const apiTokenRequest = {
  scopes: apiScope ? [apiScope] : [],
};

/** Auth feature flag — set NEXT_PUBLIC_AUTH_ENABLED=false for local dev bypass */
export const AUTH_ENABLED = process.env.NEXT_PUBLIC_AUTH_ENABLED !== 'false';
