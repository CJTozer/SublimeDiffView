import sublime_plugin


class ViewFinder(sublime_plugin.EventListener):
    """Helper class for finding widgets that are created."""
    _instance = None

    def __init__(self):
        self.__class__._instance = self
        self._listening = False

    def on_activated(self, view):
        """Call the provided callback when a widget view is created.

        Args:
            view: The view to listen for widget creation in."""
        if self._listening and view.settings().get('is_widget'):
            self._listening = False
            self.cb(view)

    @classmethod
    def instance(cls):
        if cls._instance:
            return cls._instance
        else:
            return cls()

    def start_listen(self, cb):
        """Start listening for widget creation.

        Args:
            cb: The callback to call when a widget is created."""
        self.cb = cb
        self._listening = True
