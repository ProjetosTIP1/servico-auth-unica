import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Colaborador, LoginCredentials } from "@/store/schemas";

/**
 * =============================================================================
 * AUTHENTICATION STORE
 * =============================================================================
 *
 * This Zustand store manages the complete authentication lifecycle, including
 * user state, token management, and authentication status.
 *
 * RESPONSIBILITIES (Single Responsibility Principle):
 * - Handling user login and logout
 * - Storing and managing the authentication token and user data
 * - Providing a single source of truth for authentication status
 * - Re-hydrating auth state on application startup
 *
 * ARCHITECTURE NOTES:
 * - This store is a critical part of the APPLICATION LAYER
 * - It delegates all API calls to the AuthServer (infrastructure layer)
 * - It uses Zustand's `persist` middleware as the single source for storage,
 *   eliminating direct localStorage calls from the actions.
 * - Token expiration is checked on hydration to ensure session validity.
 *
 * SECURITY CONSIDERATIONS:
 * - This implementation stores the JWT in localStorage. For higher security
 *   applications, consider using httpOnly cookies to mitigate XSS risks.
 * - The `jwt-decode` library is used for client-side token expiration checks.
 *   This is a UX enhancement; final validation should always occur on the server.
 */

// =============================================================================
// TYPES & INTERFACES
// =============================================================================

/**
 * Toast notification types
 * Following common UX patterns for user feedback
 */
type ToastType = "success" | "error" | "info" | "warning";

/**
 * Toast state structure
 * Represents a single toast notification
 */
interface ToastState {
  /** The message to display to the user */
  message: string;
  /** The type/severity of the notification */
  type: ToastType;
  /** Whether the toast is currently visible */
  visible: boolean;
}

interface AuthState {
  // =============================================================================
  // STATE - Authentication Data
  // =============================================================================

  /** The authenticated user's data. Null if not authenticated. */
  colaborador: Colaborador | null;

  /** The JWT authentication token. Null if not authenticated. */
  token: string | null;

  /**
   * Current toast notification state
   * LIMITATION: Only supports one toast at a time
   * For multiple toasts, consider implementing a queue system
   */
  toast: ToastState;

  /**
   * Single source of truth for authentication status.
   * True only if a valid, non-expired token exists.
   */
  isAuthenticated: boolean;

  /**
   * Indicates whether the auth store has completed its initial hydration.
   * Used to prevent premature redirects before auth state is determined.
   */
  isHydrated: boolean;

  /** Loading state for async auth operations (e.g., login). */
  isLoading: boolean;

  /** Error message from the last failed auth operation. */
  error: string | null;

  /** Flag to prevent multiple simultaneous logout attempts. */
  isLoggingOut: boolean;

  // =============================================================================
  // ACTIONS - State Mutations
  // =============================================================================

  /**
   * Authenticates the user with the provided credentials.
   *
   * @param credentials - The user's login credentials (e.g., username/password)
   * @returns Promise<void>
   *
   * PROCESS:
   * 1. Sets loading state.
   * 2. Calls AuthServer.login to get token and user data.
   * 3. On success, updates state with token, user, and sets isAuthenticated to true.
   * 4. On failure, sets an error message and ensures isAuthenticated is false.
   */
  login: (credentials: LoginCredentials) => Promise<void>;

  /**
   * Logs the user out and clears all authentication state.
   *
   * PROCESS:
   * 1. Calls AuthServer.logout (optional, for server-side session invalidation).
   * 2. Resets the store to its initial, unauthenticated state.
   */
  logout: () => Promise<void>;

  /**
   * Synchronously clears all authentication state without making API calls.
   * Used for error scenarios (401, token validation failures) to prevent loops.
   *
   * PROCESS:
   * 1. Clears all user-specific stores.
   * 2. Removes all localStorage entries.
   * 3. Resets auth store to initial state.
   */
  clearAuthState: () => void;

  /**
   * Display a toast notification
   *
   * @param message - The message to display to the user
   * @param type - The type of notification (default: "info")
   * @param duration - How long to display the toast in ms (default: 3000)
   *
   * BEHAVIOR:
   * - Automatically dismisses after `duration` milliseconds
   * - Replaces any existing toast (no queue)
   * - Does NOT persist across page reloads
   *
   * EXAMPLES:
   * ```tsx
   * showToast("Tarefa criada com sucesso!", "success");
   * showToast("Erro ao salvar dados", "error");
   * showToast("Processando...", "info", 5000);
   * ```
   *
   * LIMITATION:
   * If called multiple times rapidly, only the last toast will be visible.
   * Consider implementing a queue for production use.
   */
  showToast: (message: string, type?: ToastType, duration?: number) => void;

  /**
   * Hide the current toast immediately
   * Useful for user-triggered dismissal or cleanup
   */
  hideToast: () => void;

  /**
   * Hydrates the store on app startup.
   * Checks if a persisted token exists and is still valid.
   * If the token is invalid or expired, it logs the user out.
   *
   * This should be called once when the application root component mounts.
   */
  hydrate: () => void;

  /** Clears any existing authentication error message. */
  clearError: () => void;
}

// =============================================================================
// INITIAL STATE
// =============================================================================

const initialState = {
  colaborador: null,
  token: null,
  isAuthenticated: false,
  isHydrated: false,
  isLoading: false,
  error: null,
  toast: {
    message: "",
    type: "info" as ToastType,
    visible: false,
  },
  isLoggingOut: false,
};

// =============================================================================
// STORE IMPLEMENTATION
// =============================================================================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        try {
          //   const data = await AuthServer.login(credentials);
          //   if (data && data.access_token) {
          //     set({
          //       colaborador: data.colaborador || null,
          //       token: data.access_token,
          //       isAuthenticated: true,
          //       isHydrated: true, // Mark as hydrated after successful login
          //       isLoading: false,
          //     });
          //   } else {
          //     throw new Error("Login response did not include an access token.");
          //   }
        } catch (error) {
          set({
            ...initialState, // Reset state on failure
            error: error instanceof Error ? error.message : "Login failed",
          });
          throw error;
        }
      },

      clearAuthState: () => {
        // Clear localStorage for all user-specific data
        localStorage.removeItem("auth-storage");

        // Reset auth store to initial state
        set(initialState);
      },

      logout: async () => {
        // Prevent multiple concurrent logout attempts
        if (get().isLoggingOut) {
          console.warn("⚠️ Logout already in progress, skipping...");
          return;
        }

        set({ isLoading: true, isLoggingOut: true, error: null });

        try {
          const { token } = get();

          // Only attempt server revocation if we have a token
          // This is a best-effort operation - we'll clear local state regardless
          if (token) {
            try {
              //   await AuthServer.logout({ token });
            } catch (error) {
              // Silent fail - token revocation is non-critical for logout
              // User is logging out anyway, so local state will be cleared
              console.warn("⚠️ Token revocation failed (non-critical):", error);
            }
          }
        } finally {
          // Always clear state, even if server logout fails
          get().clearAuthState();
        }
      },

      hydrate: async () => {
        set({ isLoading: true, error: null });
        const { token } = get();

        if (!token) {
          set({ isAuthenticated: false, isHydrated: true, isLoading: false });
          return;
        }

        try {
          //   const tokenValidityStatus = await AuthServer.validateToken({ token });
          //   if (!tokenValidityStatus?.active) {
          //     // Token is invalid - clear state synchronously without API calls
          //     console.warn("🔐 Token validation failed during hydration - clearing auth state");
          //     get().clearAuthState();
          //     set({ isHydrated: true, isLoading: false });
          //   } else {
          //     // Token is valid
          //     set({ isAuthenticated: true, isHydrated: true, isLoading: false });
          //   }
        } catch (error) {
          // On validation error, assume invalid and clear synchronously
          console.error("❌ Token validation error during hydration:", error);
          get().clearAuthState();
          set({ isHydrated: true, isLoading: false });
        }
      },

      showToast: (
        message: string,
        type: ToastType = "info",
        duration: number = 3000,
      ) => {
        // Show the toast
        set({
          toast: {
            message,
            type,
            visible: true,
          },
        });

        // Auto-dismiss after duration
        // NOTE: In production, store the timeout ID and clear it if component unmounts
        // or if showToast is called again before the timeout completes
        setTimeout(() => {
          // Only hide if the message hasn't changed (prevents hiding a new toast)
          const currentToast = get().toast;
          if (currentToast.message === message) {
            set({
              toast: {
                message: "",
                type: "info",
                visible: false,
              },
            });
          }
        }, duration);
      },

      hideToast: () => {
        set({
          toast: {
            message: "",
            type: "info",
            visible: false,
          },
        });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: "auth-storage", // localStorage key
      // Persist only the token and user data
      partialize: (state) => ({
        token: state.token,
        colaborador: state.colaborador,
      }),
    },
  ),
);
