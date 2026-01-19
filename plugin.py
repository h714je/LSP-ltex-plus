import sublime
import sublime_plugin
import platform
import os
from LSP.plugin import (
    AbstractPlugin,
    Notification,
    register_plugin,
    unregister_plugin,
)
from LSP.plugin.core.typing import Any, Callable, List, Mapping, Optional, Dict

from .settings import SettingsManager
from .server import LTeXPlusServer


class LTeXPlus(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return "ltex-plus"

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        return LTeXPlusServer.needs_update_or_installation()

    @classmethod
    def install_or_update(cls) -> None:
        LTeXPlusServer.install_or_update()

    @classmethod
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        # bin/ltex-ls-plus is the script for linux/mac, bin/ltex-ls-plus.bat for windows
        script = "ltex-ls-plus.bat" if platform.system() == "Windows" else "ltex-ls-plus"
        return {
            "serverdir": LTeXPlusServer.serverdir(),
            "script": script,
        }

    def on_workspace_configuration(self, params: Any, configuration: Any) -> Any:
        return SettingsManager.expand_settings(configuration)

    def on_pre_server_command(
        self, command: Mapping[str, Any], done_callback: Callable[[], None]
    ) -> bool:
        session = self.weaksession()
        if not session:
            return False

        cmd_name = command.get("command")
        if not cmd_name:
            return False
            
        # Command dispatch
        if cmd_name == "_ltex.addToDictionary":
            return self._handle_add_to_dictionary(command, done_callback)
        
        if cmd_name == "_ltex.hideFalsePositives":
            return self._handle_hide_false_positives(command, done_callback)
            
        if cmd_name == "_ltex.disableRules":
            return self._handle_disable_rules(command, done_callback)

        return False

    # --- Command Handlers ---

    def _handle_add_to_dictionary(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        payload = self._get_payload(command)
        words = payload.get("words")
        if isinstance(words, dict):
            manual_update = SettingsManager.update_from_code_action("ltex.dictionary", words)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    def _handle_hide_false_positives(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        payload = self._get_payload(command)
        fps = payload.get("falsePositives")
        if isinstance(fps, dict):
            manual_update = SettingsManager.update_from_code_action("ltex.hiddenFalsePositives", fps)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    def _handle_disable_rules(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        payload = self._get_payload(command)
        rule_ids = payload.get("ruleIds")
        if isinstance(rule_ids, dict):
            manual_update = SettingsManager.update_from_code_action("ltex.disabledRules", rule_ids)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    # --- Helpers ---

    def _get_payload(self, command: Mapping[str, Any]) -> dict:
        args = command.get("arguments")
        if isinstance(args, list) and args and isinstance(args[0], dict):
            return args[0]
        return {}

    def _finalize_command(self, manual_update_needed: bool, payload: dict, done_callback: Callable[[], None]) -> None:
        """
        Completes the command execution. If manual_update_needed is True, 
        sends a didChangeConfiguration notification to the server.
        """
        if manual_update_needed:
            self._trigger_manual_update(payload)
        
        # Always call the callback to let LSP know the command is 'done' (or handled)
        sublime.set_timeout_async(done_callback)

    def _trigger_manual_update(self, payload: dict) -> None:
        """
        Manually forces the server to re-read settings and re-check the document.
        Used when we update external dictionary files without changing the actual settings map,
        so LSP doesn't automatically detect the change.
        """
        session = self.weaksession()
        if not session:
            return

        # 1. Read current Sublime settings
        sublime_settings = sublime.load_settings("LSP-ltex-plus.sublime-settings")
        user_settings = sublime_settings.get("settings", {})
        
        # 2. Expand paths -> words
        expanded_settings = SettingsManager.expand_settings(user_settings)
        
        # 3. Notify server
        session.send_notification(
            Notification("workspace/didChangeConfiguration", {"settings": expanded_settings})
        )
        
        # 4. Trigger re-check if URI is available
        uri = payload.get("uri")
        if uri:
            def delayed_check():
                session.execute_command(
                    {"command": "_ltex.checkDocument", "arguments": [{"uri": uri}]}
                )
            
            # Give the server a moment to process the config change
            sublime.set_timeout_async(delayed_check, 100)


# ============================================================================
# User Commands
# ============================================================================

class LtexClearDiagnosticsCommand(sublime_plugin.TextCommand):
    """Clear all LTeX diagnostics from the current view."""
    
    def run(self, edit: sublime.Edit) -> None:
        window = self.view.window()
        if not window:
            return
        
        # Clear diagnostics for this file
        file_name = self.view.file_name()
        if file_name:
            # Trigger a manual clear via LSP
            window.run_command("lsp_clear_panel_diagnostics")
            sublime.status_message("LTeX: Diagnostics cleared")
        else:
            sublime.status_message("LTeX: No file to clear diagnostics from")
    
    def is_enabled(self) -> bool:
        """Enable only if there's an active file."""
        return self.view.file_name() is not None


class LtexShowStatusCommand(sublime_plugin.WindowCommand):
    """Show LTeX server status and plugin information."""
    
    def run(self) -> None:
        from .server import LTeXPlusServer
        
        # Collect status information
        lines = []
        lines.append("=== LSP-ltex-plus Status ===\n")
        
        # Server version
        server_version = LTeXPlusServer.serverversion()
        lines.append(f"Server Version: {server_version}")
        
        # Server directory
        server_dir = LTeXPlusServer.serverdir()
        server_installed = "✓ Installed" if LTeXPlusServer.needs_update_or_installation() == False else "✗ Not installed"
        lines.append(f"Server Status: {server_installed}")
        lines.append(f"Server Path: {server_dir}\n")
        
        # Settings
        settings = sublime.load_settings("LSP-ltex-plus.sublime-settings")
        language = settings.get("settings", {}).get("ltex.language", "not set")
        lines.append(f"Active Language: {language}")
        
        # External files configuration
        use_ext_dict = settings.get("use_external_dictionary_files", False)
        use_ext_fps = settings.get("use_external_hidden_false_positives_files", False)
        use_ext_rules = settings.get("use_external_disabled_rules_files", False)
        lines.append(f"External Dictionary Files: {'✓ Enabled' if use_ext_dict else '✗ Disabled'}")
        lines.append(f"External False Positives: {'✓ Enabled' if use_ext_fps else '✗ Disabled'}")
        lines.append(f"External Disabled Rules: {'✓ Enabled' if use_ext_rules else '✗ Disabled'}")
        
        # Show in dialog
        sublime.message_dialog("\n".join(lines))


class LtexRestartServerCommand(sublime_plugin.WindowCommand):
    """Restart the LTeX language server."""
    
    def run(self) -> None:
        sublime.status_message("LTeX: Restarting server...")
        
        # Use LSP's built-in restart command
        self.window.run_command("lsp_restart_server", {"config_name": "ltex-plus"})
        
        # Give feedback after a delay
        def show_completion():
            sublime.status_message("LTeX: Server restart initiated")
        
        sublime.set_timeout_async(show_completion, 500)


def plugin_loaded() -> None:
    register_plugin(LTeXPlus)


def plugin_unloaded() -> None:
    unregister_plugin(LTeXPlus)
