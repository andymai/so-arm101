#!/usr/bin/env bash
# check-readme-reminders.sh - Remind to review READMEs when Python source changes.
#
# Walks up from each staged .py file's directory looking for README.md on disk.
# Zero-config: adding a README anywhere automatically joins the reminder list.
#
# Non-blocking: always exits 0. A reminder for humans and LLMs committing changes,
# not a gate.

trap 'exit 0' ERR

# Associative arrays need bash 4+; stock macOS ships 3.2. Skip quietly if unavailable
# (this is a non-blocking reminder, not a gate) so the hook never prints an error.
if ((BASH_VERSINFO[0] < 4)); then
    exit 0
fi

STAGED=$(git diff --cached --name-only --diff-filter=ACMR || true)
[ -z "$STAGED" ] && exit 0

declare -A STAGED_READMES DIR_FILE_COUNTS
HAS_SOURCE=false

while IFS= read -r FILE; do
    [ -z "$FILE" ] && continue
    case "$FILE" in */README.md|README.md) STAGED_READMES["$FILE"]=1; continue ;; esac
    case "$FILE" in *.py) ;; *) continue ;; esac
    # Skip test files — changes there rarely affect the architecture a README describes.
    case "$FILE" in
        */tests/*|test_*.py|*_test.py) continue ;;
    esac

    DIR="${FILE%/*}"
    [ "$DIR" = "$FILE" ] && DIR="."
    DIR_FILE_COUNTS["$DIR"]=$(( ${DIR_FILE_COUNTS["$DIR"]:-0} + 1 ))
    HAS_SOURCE=true
done <<< "$STAGED"

$HAS_SOURCE || exit 0

# Walk up from each directory, collecting READMEs on disk.
declare -A FOUND_READMES WALKED
for DIR in "${!DIR_FILE_COUNTS[@]}"; do
    CURRENT="$DIR"
    while true; do
        [ "${WALKED[$CURRENT]+_}" ] && break
        WALKED["$CURRENT"]=1
        [ -f "${CURRENT}/README.md" ] && FOUND_READMES["${CURRENT}/README.md"]=1
        PARENT="${CURRENT%/*}"
        [ "$PARENT" = "$CURRENT" ] && break
        CURRENT="$PARENT"
    done
done

[ ${#FOUND_READMES[@]} -eq 0 ] && exit 0

readarray -t SORTED < <(printf '%s\n' "${!FOUND_READMES[@]}" | sort)

LINES=()
for README_PATH in "${SORTED[@]}"; do
    [ "${STAGED_READMES[$README_PATH]+_}" ] && continue

    README_DIR="${README_PATH%/*}"
    FILE_COUNT=0
    for SDIR in "${!DIR_FILE_COUNTS[@]}"; do
        case "$SDIR" in "$README_DIR"|"$README_DIR"/*) FILE_COUNT=$(( FILE_COUNT + DIR_FILE_COUNTS["$SDIR"] )) ;; esac
    done

    NAME="${README_DIR##*/}"
    [ "$NAME" = "." ] && NAME="<root>"
    SUFFIX="s"; [ "$FILE_COUNT" -eq 1 ] && SUFFIX=""
    LABEL="${NAME} (${FILE_COUNT} file${SUFFIX})"
    PAD=$(( 28 - ${#LABEL} ))
    [ "$PAD" -lt 1 ] && PAD=1
    LINES+=("  ${LABEL}$(printf '%*s' "$PAD" '')→ ${README_PATH}")
done

if [ ${#LINES[@]} -gt 0 ]; then
    printf '\nREADME review reminder:\n'
    printf '%s\n' "${LINES[@]}"
    printf '  (Review these READMEs if your changes affect architecture, key files, or gotchas)\n\n'
fi

exit 0
