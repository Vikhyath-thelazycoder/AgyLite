// A small Zustand-style store.
export function createStore() {
  const state = { selectedThread: null, composeMode: false, composeData: null, archived: [] };
  return {
    get: () => ({ ...state }),
    setComposeMode(on) { state.composeMode = on; },
    selectThread(thread) {
      state.selectedThread = thread;
      state.composeMode = false;   // leaving compose when a thread is opened
      state.composeData = null;
    },
    archive(id) { state.archived.push(id); state.selectedThread = null; },
  };
}
