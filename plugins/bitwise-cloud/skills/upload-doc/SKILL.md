---
description: Upload a PDF datasheet to Bitwise Cloud for indexing
command: upload-doc
---

# Upload Document

Upload a PDF document to Bitwise Cloud for indexing.

## Steps

1. Ask the user which PDF to upload (or accept a path argument)
2. Call the `upload_doc` MCP tool with the file path and optional title
3. The tool returns a document ID — use `check_progress` to monitor ingestion
4. Poll `check_progress` periodically until status is "ready" or "failed"

## Notes

- Only PDF files are supported
- Duplicate files (same SHA256 hash) will be rejected
- Ingestion may take several minutes for large documents (1000+ pages)
- The document title defaults to the filename if not provided
