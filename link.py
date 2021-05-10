import copy
import json
import os
import platform

from platformio.managers.platform import PlatformBase


class P246Platform(PlatformBase):

    def is_embedded(self):
        return True

    def configure_default_packages(self, variables, targets):
        if variables.get("board"):
            board = variables.get("board")
            if "mbed" in variables.get("pioframework", []):
                deprecated_boards_file = os.path.join(
                    self.get_dir(), "misc", "mbed_deprecated_boards.json")
                if os.path.isfile(deprecated_boards_file):
                    with open(deprecated_boards_file) as fp:
                        if board in json.load(fp):
                            self.packages["framework-mbed"]["version"] = "~6.51506.0"

            upload_protocol = variables.get("upload_protocol", self.board_config(
                board).get("upload.protocol", ""))
            if upload_protocol == "cmsis-dap":
                self.packages["tool-pyocd"]["type"] = "uploader"

        return PlatformBase.configure_default_packages(self, variables,
                                                       targets)

    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        debug = board.manifest.get("debug", {})
        upload_protocols = board.manifest.get("upload", {}).get(
            "protocols", [])
        if "tools" not in debug:
            debug["tools"] = {}

        for link in ("jlink", ):
            if link not in upload_protocols or link in debug["tools"]:
                continue

            if link == "jlink":
                assert debug.get("jlink_device"), (
                    "Missed J-Link Device ID for %s" % board.id)
                debug["tools"][link] = {
                    "server": {
                        "package": "tool-jlink",
                        "arguments": [
                            "-singlerun",
                            "-if", "SWD",
                            "-select", "USB",
                            "-device", debug.get("jlink_device"),
                            "-port", "2331"
                        ],
                        "executable": ("JLinkGDBServerCL.exe"
                                       if platform.system() == "Windows" else
                                       "JLinkGDBServer")
                    },
                    "onboard": link in debug.get("onboard_tools", [])
                }

        board.manifest["debug"] = debug
        return board

    def configure_debug_options(self, initial_debug_options, ide_data):
        debug_options = copy.deepcopy(initial_debug_options)
        server_executable = debug_options["server"]["executable"].lower()
        adapter_speed = initial_debug_options.get("speed")
        if adapter_speed:
            if "jlink" in server_executable:
                debug_options["server"]["arguments"].extend(
                    ["-speed", adapter_speed]
                )
            elif "pyocd" in debug_options["server"]["package"]:
                assert (
                    adapter_speed.isdigit()
                ), "pyOCD requires the debug frequency value in Hz, e.g. 4000"
                debug_options["server"]["arguments"].extend(
                    ["--frequency", "%d" % int(adapter_speed)]
                )

        return debug_options
