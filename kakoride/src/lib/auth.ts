import { api, setToken } from "./api";
export async function signIn(email: string, password: string) {
  const [{ signInWithEmailAndPassword }, { auth }] = await Promise.all([import("firebase/auth"), import("../firebase")]);
  if (!auth) throw new Error("Driver authentication is not configured. Ask your administrator.");
  const credential = await signInWithEmailAndPassword(auth, email, password);
  setToken(await credential.user.getIdToken(), () => credential.user.getIdToken());
}
export async function restoreSignIn() {
  const { auth } = await import("../firebase");
  if (!auth) return;
  await auth.authStateReady();
  const user = auth.currentUser;
  if (user) setToken(await user.getIdToken(), () => user.getIdToken());
}
export async function signOut(development: boolean) {
  try { await api("/api/auth/logout", {}); } catch { /* Local credentials are cleared even offline. */ }
  if (!development) {
    const [{ signOut }, { auth }] = await Promise.all([import("firebase/auth"), import("../firebase")]);
    if (auth) await signOut(auth);
  }
  setToken("");
}
