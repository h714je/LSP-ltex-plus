import os
import shutil
import tarfile
import tempfile
import urllib.request
import urllib.error
import sublime

# Constants
GITHUB_DL_URL = "https://github.com/ltex-plus/ltex-ls-plus/releases/download/{0}/ltex-ls-plus-{0}{1}"
GITHUB_RELEASES_API_URL = "https://api.github.com/repos/ltex-plus/ltex-ls-plus/releases/latest"
SERVER_FOLDER_NAME = "ltex-ls-plus-{}"
LATEST_TESTED_RELEASE = "18.6.1"
STORAGE_FOLDER_NAME = "LSP-ltex-plus"
SETTINGS_FILENAME = "LSP-ltex-plus.sublime-settings"

class LTeXPlusServer:
    @classmethod
    def storage_path(cls) -> str:
        return os.path.join(sublime.cache_path(), "..", "Package Storage")

    @classmethod
    def basedir(cls) -> str:
        """
        The directory of this plugin in Package Storage.
        """
        return os.path.join(cls.storage_path(), STORAGE_FOLDER_NAME)

    @classmethod
    def serverversion(cls) -> str:
        """
        Returns the version of ltex-ls to use.
        """
        settings = sublime.load_settings(SETTINGS_FILENAME)
        version = settings.get("version")
        if version:
            return version
        
        return LATEST_TESTED_RELEASE

    @classmethod
    def serverdir(cls) -> str:
        """
        The directory of the server. In here are the "bin" and "lib" folders.
        """
        return os.path.join(
            cls.basedir(), SERVER_FOLDER_NAME.format(cls.serverversion())
        )

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        return not os.path.isdir(cls.serverdir())

    @classmethod
    def install_or_update(cls) -> None:
        version = cls.serverversion()
        if not version:
            return

        basedir = cls.basedir()
        if os.path.isdir(basedir):
            shutil.rmtree(basedir)
        os.makedirs(basedir)

        with tempfile.TemporaryDirectory() as tempdir:
            archive_path = os.path.join(tempdir, "server.tar.gz")
            
            # FORCE platform-independent .tar.gz (no bundled Java)
            suffix = ".tar.gz"

            sublime.status_message("LSP-ltex-plus: downloading server...")
            
            download_url = GITHUB_DL_URL.format(version, suffix)
            print(f"LSP-ltex-plus: downloading from {download_url}")
            
            try:
                urllib.request.urlretrieve(download_url, archive_path)
            except urllib.error.URLError as e:
                sublime.error_message(f"LSP-ltex-plus: Error downloading server: {e}")
                return

            sublime.status_message("LSP-ltex-plus: extracting server...")
            
            try:
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(tempdir)
            except tarfile.TarError as e:
                sublime.error_message(f"LSP-ltex-plus: Error extracting server: {e}")
                return

            # The extracted folder usually looks like "ltex-ls-plus-18.6.1"
            extracted_folder_name = SERVER_FOLDER_NAME.format(version)
            src_path = os.path.join(tempdir, extracted_folder_name)
            dst_path = basedir
            
            # Move contents to basedir so structure is .../LSP-ltex-plus/ltex-ls-plus-18.6.1/
            # wait, LTeX-ls logic moves it to basedir/SERVER_FOLDER_NAME ?
            # Let's check typical structure. default basedir is .../LSP-ltex-plus.
            # We want .../LSP-ltex-plus/ltex-ls-plus-18.6.1
            
            shutil.move(src_path, dst_path)
            
            sublime.status_message(f"LSP-ltex-plus: installed server version {version}")
