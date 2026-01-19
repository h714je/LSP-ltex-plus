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
    """
    LSP-ltex-plus plugin implementation.
    
    This plugin acts as a bridge between Sublime Text and the LTeX Plus language server,
    handling:
    - Server installation and updates
    - Settings expansion (external dictionary files)
    - Command interception for code actions (add to dictionary, disable rules, etc.)
    - Manual server notifications when external files change
    """
    
    @classmethod
    def name(cls) -> str:
        """
        Get the plugin name for LSP registration.
        
        Returns:
            Plugin name "ltex-plus" matching the configuration key.
        """
        return "ltex-plus"

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        """
        Check if server needs installation or update.
        
        Returns:
            True if server directory doesn't exist, False otherwise.
        """
        return LTeXPlusServer.needs_update_or_installation()

    @classmethod
    def install_or_update(cls) -> None:
        """
        Install or update the LTeX Plus language server.
        
        Delegates to LTeXPlusServer.install_or_update() which handles:
        - Platform detection
        - Download with progress
        - Extraction and installation
        """
        LTeXPlusServer.install_or_update()

    @classmethod
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        """
        Provide additional variables for server command template expansion.
        
        Returns:
            Dictionary with:
                - 'serverdir': Absolute path to server installation
                - 'script': Platform-specific script name (ltex-ls-plus or ltex-ls-plus.bat)
        """
        # bin/ltex-ls-plus is the script for linux/mac, bin/ltex-ls-plus.bat for windows
        script: str = "ltex-ls-plus.bat" if platform.system() == "Windows" else "ltex-ls-plus"
        return {
            "serverdir": LTeXPlusServer.serverdir(),
            "script": script,
        }

    def on_workspace_configuration(self, params: Any, configuration: Any) -> Any:
        """
        Expand workspace configuration before sending to server.
        
        This method intercepts the configuration and expands external file paths
        (e.g., ':path/to/dict.txt') with their actual content.
        
        Args:
            params: Configuration request parameters from server
            configuration: Raw configuration from Sublime settings
            
        Returns:
            Expanded configuration with external files loaded
        """
        return SettingsManager.expand_settings(configuration)

    def on_pre_server_command(
        self, command: Mapping[str, Any], done_callback: Callable[[], None]
    ) -> bool:
        """
        Intercept server commands to handle code actions with external files.
        
        When external dictionary files are enabled, we need to intercept
        code actions (add to dictionary, disable rules, hide false positives)
        to write changes to external files instead of settings.
        
        Args:
            command: Server command with 'command' and 'arguments' keys
            done_callback: Callback to invoke when command handling is complete
            
        Returns:
            True if command was intercepted and handled, False to let it through
        """
        session = self.weaksession()
        if not session:
            return False

        cmd_name: Optional[str] = command.get("command")
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
        """
        Handle '_ltex.addToDictionary' code action.
        
        Args:
            command: Command with arguments containing words to add
            done_callback: Callback to invoke when done
            
        Returns:
            True if handled successfully, False otherwise
        """
        payload: Dict[str, Any] = self._get_payload(command)
        words: Any = payload.get("words")
        if isinstance(words, dict):
            manual_update: bool = SettingsManager.update_from_code_action("ltex.dictionary", words)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    def _handle_hide_false_positives(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        """
        Handle '_ltex.hideFalsePositives' code action.
        
        Args:
            command: Command with arguments containing false positives to hide
            done_callback: Callback to invoke when done
            
        Returns:
            True if handled successfully, False otherwise
        """
        payload: Dict[str, Any] = self._get_payload(command)
        fps: Any = payload.get("falsePositives")
        if isinstance(fps, dict):
            manual_update: bool = SettingsManager.update_from_code_action("ltex.hiddenFalsePositives", fps)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    def _handle_disable_rules(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        """
        Handle '_ltex.disableRules' code action.
        
        Args:
            command: Command with arguments containing rule IDs to disable
            done_callback: Callback to invoke when done
            
        Returns:
            True if handled successfully, False otherwise
        """
        payload: Dict[str, Any] = self._get_payload(command)
        rule_ids: Any = payload.get("ruleIds")
        if isinstance(rule_ids, dict):
            manual_update: bool = SettingsManager.update_from_code_action("ltex.disabledRules", rule_ids)
            self._finalize_command(manual_update, payload, done_callback)
            return True
        return False

    # --- Helpers ---

    def _get_payload(self, command: Mapping[str, Any]) -> Dict[str, Any]:
        """
        Extract payload from server command arguments.
        
        Args:
            command: Server command containing 'arguments' list
            
        Returns:
            First argument as dictionary, or empty dict if not found
        """
        args: Any = command.get("arguments")
        if isinstance(args, list) and args and isinstance(args[0], dict):
            return args[0]
        return {}

    def _finalize_command(self, manual_update_needed: bool, payload: Dict[str, Any], done_callback: Callable[[], None]) -> None:
        """
        Complete command execution and notify server if needed.
        
        When external files are updated, the settings map doesn't change,
        so we need to manually trigger a server configuration update.
        
        Args:
            manual_update_needed: Whether to send didChangeConfiguration notification
            payload: Command payload containing file URI
            done_callback: Callback to invoke to complete command execution
        """
        if manual_update_needed:
            self._trigger_manual_update(payload)
        
        # Always call the callback to let LSP know the command is 'done' (or handled)
        sublime.set_timeout_async(done_callback)

    def _trigger_manual_update(self, payload: Dict[str, Any]) -> None:
        """
        Manually force server to re-read settings and re-check document.
        
        This is needed when external dictionary files change without the settings
        map changing. Since LSP doesn't automatically detect external file changes,
        we must manually:
        1. Re-expand external file paths to their content
        2. Send didChangeConfiguration notification
        3. Trigger document re-check
        
        Args:
            payload: Command payload containing document URI
        """
        session = self.weaksession()
        if not session:
            return

        # 1. Read current Sublime settings
        sublime_settings: sublime.Settings = sublime.load_settings("LSP-ltex-plus.sublime-settings")
        user_settings: Dict[str, Any] = sublime_settings.get("settings", {})
        
        # 2. Expand paths -> words
        expanded_settings: Dict[str, Any] = SettingsManager.expand_settings(user_settings)
        
        # 3. Notify server
        session.send_notification(
            Notification("workspace/didChangeConfiguration", {"settings": expanded_settings})
        )
        
        # 4. Trigger re-check if URI is available
        uri: Optional[str] = payload.get("uri")
        if uri:
            def delayed_check() -> None:
                session.execute_command(
                    {"command": "_ltex.checkDocument", "arguments": [{"uri": uri}]}
                )
            
            # Give the server a moment to process the config change
            sublime.set_timeout_async(delayed_check, 100)


# ============================================================================
# User Commands
# ============================================================================

class LtexClearDiagnosticsCommand(sublime_plugin.TextCommand):
    """
    Clear all LTeX diagnostics from the current view.
    
    This command clears the LSP diagnostics panel, removing all grammar
    and spelling errors from display.
    """
    
    def run(self, edit: sublime.Edit) -> None:
        """
        Execute the clear diagnostics command.
        
        Args:
            edit: Edit object for text modifications (unused here)
        """
        window: Optional[sublime.Window] = self.view.window()
        if not window:
            return
        
        # Clear diagnostics for this file
        file_name: Optional[str] = self.view.file_name()
        if file_name:
            # Trigger a manual clear via LSP
            window.run_command("lsp_clear_panel_diagnostics")
            sublime.status_message("LTeX: Diagnostics cleared")
        else:
            sublime.status_message("LTeX: No file to clear diagnostics from")
    
    def is_enabled(self) -> bool:
        """
        Check if command should be enabled.
        
        Returns:
            True if view has an associated file, False otherwise
        """
        return self.view.file_name() is not None


class LtexShowStatusCommand(sublime_plugin.WindowCommand):
    """
    Show LTeX server status and plugin information.
    
    Displays a dialog with:
    - Server version and installation status
    - Active language setting
    - External files configuration
    """
    
    def run(self) -> None:
        """
        Execute the show status command.
        
        Gathers server and configuration information and displays it
        in a modal dialog.
        """
        from .server import LTeXPlusServer
        
        # Collect status information
        lines: List[str] = []
        lines.append("=== LSP-ltex-plus Status ===\n")
        
        # Server version
        server_version: str = LTeXPlusServer.serverversion()
        lines.append(f"Server Version: {server_version}")
        
        # Server directory
        server_dir: str = LTeXPlusServer.serverdir()
        server_installed: str = "✓ Installed" if LTeXPlusServer.needs_update_or_installation() == False else "✗ Not installed"
        lines.append(f"Server Status: {server_installed}")
        lines.append(f"Server Path: {server_dir}\n")
        
        # Settings
        settings: sublime.Settings = sublime.load_settings("LSP-ltex-plus.sublime-settings")
        language: str = settings.get("settings", {}).get("ltex.language", "not set")
        lines.append(f"Active Language: {language}")
        
        # External files configuration
        use_ext_dict: bool = settings.get("use_external_dictionary_files", False)
        use_ext_fps: bool = settings.get("use_external_hidden_false_positives_files", False)
        use_ext_rules: bool = settings.get("use_external_disabled_rules_files", False)
        lines.append(f"External Dictionary Files: {'✓ Enabled' if use_ext_dict else '✗ Disabled'}")
        lines.append(f"External False Positives: {'✓ Enabled' if use_ext_fps else '✗ Disabled'}")
        lines.append(f"External Disabled Rules: {'✓ Enabled' if use_ext_rules else '✗ Disabled'}")
        
        # Show in dialog
        sublime.message_dialog("\n".join(lines))


class LtexRestartServerCommand(sublime_plugin.WindowCommand):
    """
    Restart the LTeX language server.
    
    This command triggers a full server restart, which can be useful:
    - After changing settings that require restart
    - When recovering from server errors
    - After manual dictionary file edits
    """
    
    def run(self) -> None:
        """
        Execute the restart server command.
        
        Delegates to LSP's built-in restart command and provides
        user feedback via status messages.
        """
        sublime.status_message("LTeX: Restarting server...")
        
        # Use LSP's built-in restart command
        self.window.run_command("lsp_restart_server", {"config_name": "ltex-plus"})
        
        # Give feedback after a delay
        def show_completion() -> None:
            sublime.status_message("LTeX: Server restart initiated")
        
        sublime.set_timeout_async(show_completion, 500)


def plugin_loaded() -> None:
    register_plugin(LTeXPlus)


def plugin_unloaded() -> None:
    unregister_plugin(LTeXPlus)
