# items/kernel.py
import pkgutil
import importlib
import traceback

class KernelContext:
    def __init__(self, kernel, plugin_name):
        self.kernel = kernel
        self.plugin_name = plugin_name

    def register_service(self, name, service):
        self.kernel.services[name] = service

    def get_service(self, name):
        return self.kernel.services.get(name)

class Kernel:
    def __init__(self):
        self.services = {}
        self.plugins = {}
        self.active_plugin = None

    def discover_and_load(self, package):
        for finder, name, ispkg in pkgutil.iter_modules(package.__path__):
            module_name = f"{package.__name__}.{name}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "Plugin"):
                    plugin = module.Plugin()
                    ctx = KernelContext(self, plugin.name())
                    plugin.init(ctx)
                    self.plugins[plugin.name()] = plugin
                    print(f"[kernel] Loaded {plugin.name()}")
            except Exception:
                traceback.print_exc()

    def activate_plugin(self, plugin_name):
        if plugin_name in self.plugins:
            self.active_plugin = self.plugins[plugin_name]
            print(f"[kernel] Activated {plugin_name}")
        else:
            print(f"[kernel] Plugin {plugin_name} not found")

    def execute(self, action, *args, **kwargs):
        if not self.active_plugin:
            raise Exception("No active plugin")
        return self.active_plugin.execute(action, *args, **kwargs)
