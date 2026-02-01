#!/bin/bash
set -e

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Skip if no file path
[[ -z "$FILE_PATH" ]] && exit 0

# Change to project directory
cd "$CLAUDE_PROJECT_DIR" || exit 1

FILE_EXT="${FILE_PATH##*.}"

# Run checks based on file type
case "$FILE_EXT" in
  js)
    npx eslint "$FILE_PATH" 2>&1
    npx tsc --noEmit 2>&1
    ;;
  css)
    npx stylelint "$FILE_PATH" 2>&1
    ;;
esac
