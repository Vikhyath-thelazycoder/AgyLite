// Button handlers of the inbox screen.
export const buttons = {
  "New Email": (store) => {
    store.setComposeMode(true);
    store.selectThread(null);
  },
  "Archive": (store, id) => store.archive(id),
  "Open": (store, thread) => store.selectThread(thread),
};
