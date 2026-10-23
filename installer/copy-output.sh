#!/data/data/com.termux/files/usr/bin/bash
set -u

usage() {
    cat <<'EOF'
PEMS clipboard helper

Pemakaian:
  bash installer/copy-output.sh <perintah> [argumen...]
  bash installer/copy-output.sh --file <file>
  bash installer/copy-output.sh --text <teks>
  <perintah> | bash installer/copy-output.sh

Perintah dijalankan atau input dibaca, ditampilkan ke terminal, lalu disalin
ke clipboard Android melalui termux-clipboard-set.
EOF
}

if ! command -v termux-clipboard-set >/dev/null 2>&1; then
    echo "ERROR: termux-clipboard-set tidak ditemukan." >&2
    echo "Pasang Termux:API: pkg install termux-api" >&2
    echo "Pastikan aplikasi Termux:API juga terpasang dari sumber yang sama." >&2
    exit 127
fi

tmp_file="$(mktemp "${TMPDIR:-/tmp}/pems-copy.XXXXXX")" || exit 1
cleanup() {
    rm -f "$tmp_file"
}
trap cleanup EXIT

command_status=0
case "${1:-}" in
    "")
        cat >"$tmp_file"
        ;;
    --help|-h)
        usage
        exit 0
        ;;
    --file)
        if [ "$#" -ne 2 ] || [ ! -f "$2" ]; then
            echo "ERROR: gunakan --file dengan file yang tersedia." >&2
            exit 2
        fi
        cat "$2" >"$tmp_file"
        ;;
    --text)
        if [ "$#" -ne 2 ]; then
            echo "ERROR: gunakan --text dengan satu nilai teks." >&2
            exit 2
        fi
        printf '%s\n' "$2" >"$tmp_file"
        ;;
    *)
        "$@" >"$tmp_file" 2>&1
        command_status=$?
        ;;
esac

cat "$tmp_file"
if ! termux-clipboard-set <"$tmp_file"; then
    echo "ERROR: output tampil, tetapi gagal disalin ke clipboard." >&2
    [ "$command_status" -ne 0 ] && exit "$command_status"
    exit 1
fi

echo "[PEMS] Output sudah disalin ke clipboard Android." >&2
exit "$command_status"
