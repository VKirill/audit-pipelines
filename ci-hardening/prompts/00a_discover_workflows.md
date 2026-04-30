# 00a — Workflows discovery

```bash
for f in .github/workflows/*.{yml,yaml}; do
  echo "=== $f ==="
  yq '.name, (.jobs | keys), .on' "$f" 2>/dev/null || cat "$f" | head -30
done
```

Для каждого workflow зафиксируй:
- name
- triggers (`on:` keys)
- jobs (count + names)
- permissions (workflow-level и per-job)
- secrets used (`${{ secrets.* }}`)
- third-party actions (`uses:` non-actions/* и не github/)

Сохрани в evidence/01_phase/workflows_inventory.md.
