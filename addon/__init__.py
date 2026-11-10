"""Optional Blender add-on for an already-open session. Configure the bridge source first."""
bl_info = {"name": "Codex Studio Bridge", "author": "YZ2020CHINA", "version": (1, 1, 0),
           "blender": (4, 2, 0), "category": "System", "location": "Preferences > Add-ons"}
import sys
from pathlib import Path
import bpy

_bridge = None


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    source: bpy.props.StringProperty(name="Plugin source folder", subtype="DIR_PATH")
    config: bpy.props.StringProperty(name="config.json", subtype="FILE_PATH")

    def draw(self, context):
        self.layout.prop(self, "source")
        self.layout.prop(self, "config")
        self.layout.operator("codex.start_bridge")
        self.layout.operator("codex.stop_bridge")


class StartBridge(bpy.types.Operator):
    bl_idname = "codex.start_bridge"
    bl_label = "Connect to Codex"

    def execute(self, context):
        global _bridge
        if _bridge and not _bridge.stopped:
            return {"FINISHED"}
        prefs = context.preferences.addons[__name__].preferences
        source = Path(bpy.path.abspath(prefs.source))
        config = Path(bpy.path.abspath(prefs.config))
        if not (source / "blender_codex/bridge.py").is_file() or not config.is_file():
            self.report({"ERROR"}, "Set the plugin source directory and an existing config.json")
            return {"CANCELLED"}
        sys.path.insert(0, str(source))
        from blender_codex.common import load_config
        from blender_codex.bridge import start
        _bridge = start(load_config(config))
        return {"FINISHED"}


class StopBridge(bpy.types.Operator):
    bl_idname = "codex.stop_bridge"
    bl_label = "Disconnect Codex"

    def execute(self, context):
        global _bridge
        if _bridge:
            if bpy.app.timers.is_registered(_bridge.drain):
                bpy.app.timers.unregister(_bridge.drain)
            _bridge.stop()
            _bridge = None
        return {"FINISHED"}


CLASSES = (CodexPreferences, StartBridge, StopBridge)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    if _bridge:
        StopBridge.execute(None, bpy.context)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
