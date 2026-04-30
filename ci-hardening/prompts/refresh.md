# Refresh — обновление manifest

При вызове `bash ci-hardening/init.sh --refresh`:

1. Прочитай существующий `manifest.yml`
2. Compare git_head: какие workflow файлы изменились?
3. Re-run только изменённые секции (workflows / actions / branch protection)
4. Update `refresh_state` в manifest
5. Validate
