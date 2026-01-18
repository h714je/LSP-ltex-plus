

# LSP-ltex-plus

Latex/Markdown grammar check support for Sublime's LSP plugin provided through [ltex-plus/ltex-ls-plus](https://github.com/ltex-plus/ltex-ls-plus).

This plugin is a fork of [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls) adapted for LTeX Plus.


## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) via Package Control.
2. Install this plugin.
3. Restart Sublime. The server will be downloaded automatically (requires internet connection).

**Requirements:**
- Java Runtime Environment (JRE) 21 or higher must be installed and available in your system PATH or configured via `JAVA_HOME`.
  - This plugin downloads the platform-independent version of `ltex-ls-plus` which does **not** include a bundled Java runtime.

Note: Currently LSP ignores non-workspace files. Add the folder to Sublime Text to enable the Server.

## Configuration

Here are some ways to configure the package and the language server.

- From `Preferences > Package Settings > LSP > Servers > LSP-ltex-plus`
- Project-specific configuration.
  From the command palette run `Project: Edit Project` and add your settings in:

  ```js
  {
     "settings": {
        "LSP": {
           "ltex-plus": {
              "settings": {
                 // Put your settings here
              }
           }
        }
     }
  }
  ```

### Language Configuration
- Set the language string in the server settings
- Use magic comments in code, see https://ltex-plus.github.io/ltex-plus/advanced-usage.html#magic-comments

### External Files

This plugin supports storing dictionaries, hidden false positives, and disabled rules in external files. This is useful for sharing configurations or keeping your settings file clean.

To enable this feature, add the following to your `LSP-ltex-plus.sublime-settings`:

```json
{
  "use_external_dictionary_files": true,
  "use_external_hidden_false_positives_files": true,
  "use_external_disabled_rules_files": true
}
```

When enabled, code actions (Add to Dictionary, Hide False Positive, Disable Rule) will write to files in your User package directory instead of updating the settings file directly.

**Default Locations:**
*   Dictionaries: `.../Packages/User/LSP-ltex-plus/dictionaries/{lang}.txt`
*   Hidden False Positives: `.../Packages/User/LSP-ltex-plus/hidden_false_positives/hiddenFalsePositives.{lang}.txt`
*   Disabled Rules: `.../Packages/User/LSP-ltex-plus/disabled_rules/disabledRules.{lang}.txt`

**Custom Locations:**
You can customize the directories by setting:
*   `external_dictionary_dir`
*   `external_hidden_false_positives_dir`
*   `external_disabled_rules_dir`

Example:
```json
{
  "use_external_dictionary_files": true,
  "external_dictionary_dir": "~/Dropbox/ltex/dictionaries"
}
```


## Credits

*   Based on [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls).
*   Powered by [ltex-plus](https://github.com/ltex-plus/ltex-ls-plus).
