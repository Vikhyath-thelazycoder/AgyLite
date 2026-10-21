# Discussion: tags for notes (2026-10-14, Mia and the agent)

- Mia: people want to group notes. Folders are too rigid; tags it is.
- Decided: a note can have up to 10 tags. Tags are lowercase, trimmed, 1–30 characters, letters, digits and dashes.
- Decided: typing `#word` in the note body does NOT create a tag; tags are added in a tag field under the title.
- Decided: the sidebar lists every tag with its note count; clicking a tag filters the list to notes with that tag.
- Decided: filtering by two tags shows notes that have BOTH (AND), not either.
- Decided: deleting the last note with a tag removes the tag from the sidebar; there is no separate tag management.
- Decided: tags are stored on the note (`tags: string[]`) in the same localStorage record; no migration of old notes
  is needed beyond treating a missing `tags` as an empty list.
- Not now: tag colours, renaming a tag across notes, sharing, sync.
- Testing: the store is the seam; test it through `saveNote` / `loadNotes` and a new `notesWithTags(tags)`.
