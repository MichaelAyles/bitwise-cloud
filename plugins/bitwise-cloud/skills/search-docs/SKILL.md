---
description: Search cloud-indexed embedded systems documentation
command: search-docs
---

# Search Documents

Search embedded systems documentation that has been indexed in Bitwise Cloud.

## Steps

1. Use the `search_docs` MCP tool with the user's query
2. For exact register name lookups (e.g. "MCR", "CTRL"), prefer the `find_register` tool — it returns structured register definitions with bit fields
3. For broader questions (e.g. "how does UART baud rate work"), use `search_docs`
4. Present results with document titles, sections, and page numbers for reference

## Notes

- Search uses hybrid keyword + semantic matching for best results
- Use `doc_filter` to restrict search to specific documents (comma-separated IDs)
- If no documents are indexed yet, suggest using the `upload-doc` skill first
