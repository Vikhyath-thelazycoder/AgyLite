const KEY = 'notes.v1';

export function loadNotes() {
  return JSON.parse(localStorage.getItem(KEY) || '[]');
}

export function saveNote(note) {
  const notes = loadNotes().filter((n) => n.id !== note.id);
  notes.push({ ...note, updatedAt: Date.now() });
  localStorage.setItem(KEY, JSON.stringify(notes));
  return note;
}

export function deleteNote(id) {
  localStorage.setItem(KEY, JSON.stringify(loadNotes().filter((n) => n.id !== id)));
}
