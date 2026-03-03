---
description: Scan local PDFs and check cloud indexing status
command: list-docs
---

# List Documents

Scan the local directory for PDF files and compare against the Bitwise Cloud index.

## Steps

1. Call the `list_docs` MCP tool with the project directory (default: current directory)
2. The tool will show three groups:
   - **Cloud-Indexed**: local PDFs that are already uploaded and indexed
   - **Local Only**: PDFs found locally but not yet uploaded
   - **Cloud Only**: documents in the cloud not found in the local directory
3. Suggest uploading any "Local Only" PDFs that look like datasheets or reference manuals

## Notes

- Hidden directories (starting with `.`) are skipped during scanning
- File matching uses SHA256 hashes — renamed files will still match
