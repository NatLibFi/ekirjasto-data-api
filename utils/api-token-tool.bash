#!/usr/bin/env bash
set -euo pipefail

# === Defaults you can change ===
DEFAULT_HOST="localhost"
DEFAULT_PORT="5432"
DEFAULT_USER="palace"
DEFAULT_DB="circ"

# This utility is an interactive helper for inserting and removing API tokens
# that live in the circulation manager database. It walks through connection
# setup, shows available collections, and exposes a small menu for viewing,
# creating, and deleting tokens. All SQL statements are executed through the
# `psql` binary so that we can pipe queries via here-documents and keep the
# script self-contained.

echo "=== Api Token Utility ==="

# --- Connection info ---
read -p "Host [${DEFAULT_HOST}]: " PGHOST
PGHOST=${PGHOST:-$DEFAULT_HOST}

read -p "Port [${DEFAULT_PORT}]: " PGPORT
PGPORT=${PGPORT:-$DEFAULT_PORT}

read -p "Username [${DEFAULT_USER}]: " PGUSER
PGUSER=${PGUSER:-$DEFAULT_USER}

read -s -p "Password: " PGPASSWORD
echo
read -p "Database [${DEFAULT_DB}]: " PGDATABASE
PGDATABASE=${PGDATABASE:-$DEFAULT_DB}

export PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE

cleanup() {
  unset PGPASSWORD
}
trap cleanup EXIT

require_psql() {
  command -v psql >/dev/null 2>&1 || {
    echo "ERROR: psql not found (install the PostgreSQL client tools)."
    exit 2
  }
}

require_openssl() {
  command -v openssl >/dev/null 2>&1 || {
    echo "ERROR: openssl not found (needed to generate random tokens)."
    exit 2
  }
}

require_psql

# psql base args (quiet, tuples only, tab-separated)
PSQLQ=(psql -X -v "ON_ERROR_STOP=1" -At -F $'\t')

# The helper functions below keep the menu logic readable. Each SQL helper
# streams a tab-separated result set back to the caller so we can format it
# nicely in the terminal without relying on external tooling.

# --- Helpers ---
abort() { echo "Aborted."; exit 1; }

sql_escape() {
  # escape single quotes for SQL literal
  local s=${1//\'/\'\'}
  printf '%s' "$s"
}

list_collections() {
  # Returns TSV: collection_id  collection_name for LICENSE_GOAL
  # The SQL is kept in a heredoc so it can be reused without duplicating
  # multi-line statements inline with the menu logic.
  "${PSQLQ[@]}" <<'SQL'
SELECT c.id,
       ic.name
FROM collections c
JOIN integration_configurations ic
  ON ic.id = c.integration_configuration_id
WHERE ic.goal = 'LICENSE_GOAL'
ORDER BY c.id;
SQL
}

show_collections_menu() {
  echo
  echo "========================================"
  echo "Eligible collections (goal = LICENSE_GOAL):"
  echo "----------------------------------------"
  printf "%-4s %-40s\n" "No" "collection name"
  echo "----------------------------------------"
  local rows
  # `mapfile` / `readarray` isn't available in macOS's default bash (3.2).
  # Use a portable read-loop to populate the array instead.
  rows=()
  while IFS= read -r line; do
    rows+=("$line")
  done < <(list_collections)

  if (( ${#rows[@]} == 0 )); then
    echo "  (none found)"
    return 1
  fi

  local i=1
  for r in "${rows[@]}"; do
    IFS=$'\t' read -r cid name <<<"$r"
    printf "[%2d] %-40s\n" "$i" "${name:-}"
    ((i++))
  done

  # Export for selection step
  COLLECTION_ROWS=("${rows[@]}")
  return 0
}

view_tokens() {
  # Formats and prints every API token along with its collection for auditing.
  echo
    echo "========================================"
    echo "All tokens (grouped by collection, newest first):"
    echo "WARNING: Full token values are shown below."
    echo "----------------------------------------"
    # Print a tab-separated header and an underline, then output aligned rows
    printf "%-40s\t%-20s\t%-40s\t%s\n" "Collection name" "Token label" "Token" "Creation date"
    printf "%-40s\t%-20s\t%-40s\t%s\n" "----------------------------------------" "--------------------" "----------------------------------------" "-------------------"

    # Query returns tab-separated columns which we format with printf for alignment.
    while IFS=$'\t' read -r cname label token created; do
      printf "%-40s\t%-20s\t%-40s\t%s\n" "${cname:-}" "${label:-}" "${token:-}" "${created:-}"
    done < <(
      "${PSQLQ[@]}" <<'SQL'
SELECT
  COALESCE(ic.name, '') AS collection_name,
  ap.label,
  ap.token,
  to_char(ap.created, 'YYYY-MM-DD HH24:MI:SS') AS created
FROM apitokens ap
LEFT JOIN collections c ON ap.collection_id = c.id
LEFT JOIN integration_configurations ic ON c.integration_configuration_id = ic.id
ORDER BY COALESCE(ic.name, '') NULLS FIRST, ap.created DESC NULLS LAST;
SQL
    )
}

create_token() {
  # Prompts the user to select a collection, enter a label, and insert a
  # freshly generated token record tied to that collection.
  require_openssl
  echo
  echo "== Create new token =="

  if ! show_collections_menu; then
    echo "Cannot create token: no eligible collections."
    echo "Returning to main menu."
    return 0
  fi

  local choice
  read -p "Select collection by number: " choice
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid selection. Returning to main menu."
    return 0
  fi
  if (( choice < 1 || choice > ${#COLLECTION_ROWS[@]} )); then
    echo "Selection out of range. Returning to main menu."
    return 0
  fi

  local selected="${COLLECTION_ROWS[choice-1]}"
  IFS=$'\t' read -r COLLECTION_ID COLLECTION_NAME <<<"$selected"

  local LABEL
  read -p "Token label (who/what is this for): " LABEL
  [[ -z "$LABEL" ]] && { echo "Label cannot be empty."; return 1; }

  # Generate a long random token (64 hex chars = 256-bit value). Adjust size if you want.
  local TOKEN
  TOKEN="$(openssl rand -hex 32)"

  echo
  echo "About to insert token:"
  echo "  collection name: ${COLLECTION_NAME:-}" 
  echo "  label:         $LABEL"
  echo "  token:         $TOKEN"
  read -p "Proceed? [y/N] " ok
  [[ "$ok" =~ ^[Yy]$ ]] || abort

  # Escape label & token for SQL
  local LABEL_ESC TOKEN_ESC
  LABEL_ESC=$(sql_escape "$LABEL")
  TOKEN_ESC=$(sql_escape "$TOKEN")

  "${PSQLQ[@]}" -c "
    INSERT INTO apitokens (token, label, collection_id, created)
    VALUES ('$TOKEN_ESC', '$LABEL_ESC', $COLLECTION_ID, current_timestamp);
  "

  echo "✅ Token inserted."
}

delete_token() {
  # Enumerates tokens so the user can choose one for removal. If the
  # `apitokens` table exposes an `id`, it is used for deletion; otherwise
  # the token string itself is deleted.
  echo
  echo "== Delete a token =="

  # Pull rows: id (if present), token, label, collection_id, created
  local rows
  rows=()
  while IFS= read -r line; do
    rows+=("$line")
  done < <("${PSQLQ[@]}" <<'SQL'
WITH cols AS (
  SELECT (SELECT COUNT(*) FROM information_schema.columns
          WHERE table_name='apitokens' AND column_name='id') AS has_id
)
SELECT
  CASE WHEN has_id>0 THEN ap.id::text ELSE '' END,
  ap.token,
  ap.label,
  ap.collection_id::text,
  COALESCE(ic.name, '') AS collection_name,
  to_char(ap.created, 'YYYY-MM-DD HH24:MI:SS')
FROM apitokens ap
LEFT JOIN collections c ON ap.collection_id = c.id
LEFT JOIN integration_configurations ic ON c.integration_configuration_id = ic.id,
cols
ORDER BY ap.created DESC NULLS LAST;
SQL
)

  if (( ${#rows[@]} == 0 )); then
    echo "  (no tokens found)"
    return 1
  fi

  # Print header like view_tokens for readability
  printf "%3s  %-40s\t%-20s\t%-40s\t%s\n" "No" "Collection name" "Token label" "Token" "Creation date"
  printf "%3s  %-40s\t%-20s\t%-40s\t%s\n" "---" "----------------------------------------" "--------------------" "----------------------------------------" "-------------------"

  local i=1
  for r in "${rows[@]}"; do
    IFS=$'\t' read -r tid token label cid collection_name created <<<"$r"
    # Print index and aligned columns (collection name, label, token, created)
    printf "%3d) %-40s\t%-20s\t%-40s\t%s\n" "$i" "${collection_name:-}" "${label:-}" "${token:-}" "${created:-}"
    ((i++))
  done

  local choice
  read -p "Select token to delete by number: " choice
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid selection. Returning to main menu."
    return 0
  fi
  if (( choice < 1 || choice > ${#rows[@]} )); then
    echo "Selection out of range. Returning to main menu."
    return 0
  fi

  local selected="${rows[choice-1]}"
  # Parse selected row into six fields: id, token, label, collection_id, collection_name, created
  IFS=$'\t' read -r TID TTOKEN TLABEL TCID TCOLLECTION_NAME TCREATED <<<"$selected"

  echo
  if [[ -n "$TID" ]]; then
    echo "About to DELETE token with id=$TID (label='${TLABEL:-}')"
  else
    echo "About to DELETE token with token='${TTOKEN}' (label='${TLABEL:-}')"
  fi
  read -p "Proceed? [y/N] " ok
  [[ "$ok" =~ ^[Yy]$ ]] || { echo "Aborted."; return 1; }

  if [[ -n "$TID" ]]; then
    # delete by id
    "${PSQLQ[@]}" -c "DELETE FROM apitokens WHERE id = $TID;"
  else
    # delete by token (escape it)
    local TOK_ESC
    TOK_ESC=$(sql_escape "$TTOKEN")
    "${PSQLQ[@]}" -c "DELETE FROM apitokens WHERE token = '$TOK_ESC';"
  fi

  echo "✅ Token deleted."
}

main_menu() {
  while true; do
    echo
    echo "Menu:"
    echo "  1) List collections"
    echo "  2) View tokens"
    echo "  3) Create new token"
    echo "  4) Delete token"
    echo "  5) Quit"
    read -p "Choose [1-5]: " ans
    case "$ans" in
      1) show_collections_menu ;;
      2) view_tokens ;;
      3) create_token ;;
      4) delete_token ;;
      5) echo "Bye!"; break ;;
      *)
        echo "Unknown choice. Returning to main menu."
        continue ;;
    esac
  done
}

# Smoke test connection (fast query)
"${PSQLQ[@]}" -c "SELECT current_database(), current_user;" >/dev/null || {
  echo "Failed to connect to database with provided credentials."
  exit 3
}

# On launch, show eligible collections to give the user immediate context
echo
show_collections_menu || true

main_menu

