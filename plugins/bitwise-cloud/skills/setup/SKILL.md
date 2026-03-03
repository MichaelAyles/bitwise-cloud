---
description: Set up Bitwise Cloud API key for authentication
command: setup
---

# Setup Bitwise Cloud

Help the user configure their Bitwise Cloud API key.

## Steps

1. Tell the user to get an API key from https://bitwise.mikeayles.com/api-keys
   - They need to create an account and generate a key (starts with `bw_`)
2. Once they have the key, use the `set_api_key` MCP tool to save it
3. Verify the connection works by calling `list_docs` to check cloud status

## Notes

- API keys are stored locally at `~/.config/bitwise-cloud/config.json`
- The `BITWISE_API_KEY` environment variable can also be used
- The `BITWISE_API_URL` environment variable overrides the default server URL
