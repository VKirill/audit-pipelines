# Security Policy

## Поддерживаемые версии

Обновляется по мере выхода релизов. Безопасность patches применяются только к последнему major.

## Сообщить об уязвимости

**Не открывай публичный issue.**

Используй [Private Vulnerability Reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) через вкладку Security в репозитории, либо напиши на security@<your-domain>.

Что включить в репорт:
- Описание уязвимости
- Шаги для воспроизведения
- Версия / commit где найдено
- Возможные impact и сценарии эксплуатации

Время реакции:
- Acknowledge: 48 часов
- Fix или mitigation plan: 7 дней
- Public disclosure: после релиза патча, обычно 30-90 дней

## Скоуп

В скоупе:
- Код в этом репозитории
- CI/CD конфигурация (`.github/`)
- Зависимости в production-сборке

Вне скоупа:
- DoS, требующие огромных ресурсов
- Социальная инженерия
- Уязвимости в зависимостях третьих сторон (репортить им напрямую)
