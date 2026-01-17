Перенесено в https://github.com/sublimelsp/LSP-ltex-plus

# LSP-ltex-plus

Поддержка проверки грамматики LaTeX/Markdown для плагина LSP в Sublime Text, обеспечиваемая через [ltex-plus/ltex-ls-plus](https://github.com/ltex-plus/ltex-ls-plus).

## Установка

1. Установите [LSP](https://packagecontrol.io/packages/LSP) через Package Control.
2. Скачайте `ltex-ls-plus` из [релизов](https://github.com/ltex-plus/ltex-ls-plus/releases).
3. Установите этот плагин.
4. Перезапустите Sublime.
5. Установите параметр `command` в настройках, указав путь к скачанному бинарному файлу `ltex-ls-plus`.

Примечание: В настоящее время LSP игнорирует файлы, не входящие в рабочую область. Добавьте папку в Sublime Text, чтобы включить сервер.

## Настройка

Вот несколько способов настройки пакета и языкового сервера.

- Через `Preferences > Package Settings > LSP > Servers > LSP-ltex-plus`
- Настройка для конкретного проекта.
  Из палитры команд запустите `Project: Edit Project` и добавьте свои настройки в:

  ```js
  {
     "settings": {
        "LSP": {
           "ltex-plus": {
              "settings": {
                 // Поместите ваши настройки здесь
              }
           }
        }
     }
  }
  ```

### Настройка языка
- Установите строку языка в настройках сервера
- Используйте "магические комментарии" в коде, см. https://ltex-plus.github.io/ltex-plus/advanced-usage.html#magic-comments

### Внешние файлы

Этот плагин поддерживает хранение словарей, скрытых ложных срабатываний и отключенных правил во внешних файлах. Это полезно для совместного использования конфигураций или поддержания чистоты файла настроек.

Чтобы включить эту функцию, добавьте следующее в ваш `LSP-ltex-ls-dev.sublime-settings`:

```json
{
  "use_external_dictionary_files": true,
  "use_external_hidden_false_positives_files": true,
  "use_external_disabled_rules_files": true
}
```

Когда включено, действия с кодом (Добавить в словарь, Скрыть ложное срабатывание, Отключить правило) будут записывать данные в файлы в директории вашего пакета User вместо обновления файла настроек напрямую.

**Расположение по умолчанию:**
*   Словари: `.../Packages/User/LSP-ltex-ls-dev/dictionaries/{lang}.txt`
*   Скрытые ложные срабатывания: `.../Packages/User/LSP-ltex-ls-dev/hidden_false_positives/hiddenFalsePositives.{lang}.txt`
*   Отключенные правила: `.../Packages/User/LSP-ltex-ls-dev/disabled_rules/disabledRules.{lang}.txt`

**Пользовательское расположение:**
Вы можете настроить директории, задав параметры:
*   `external_dictionary_dir`
*   `external_hidden_false_positives_dir`
*   `external_disabled_rules_dir`

Пример:
```json
{
  "use_external_dictionary_files": true,
  "external_dictionary_dir": "~/Dropbox/ltex/dictionaries"
}
```
