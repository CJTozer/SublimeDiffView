import sublime


class Constants(object):
    """Class whose sole purpose is storing a few constants for easy import."""
    ADD_REGION_KEY = 'diffview-highlight-addition'
    MOD_REGION_KEY = 'diffview-highlight-modification'
    DEL_REGION_KEY = 'diffview-highlight-deletion'
    ADD_REGION_STYLE = 'markup.inserted'
    MOD_REGION_STYLE = 'markup.changed'
    DEL_REGION_STYLE = 'markup.deleted'
    ADD_REGION_FLAGS = (sublime.DRAW_EMPTY |
                        sublime.HIDE_ON_MINIMAP |
                        sublime.DRAW_EMPTY_AS_OVERWRITE |
                        sublime.DRAW_NO_FILL)
    MOD_REGION_FLAGS = (sublime.DRAW_EMPTY |
                        sublime.HIDE_ON_MINIMAP |
                        sublime.DRAW_NO_FILL)
    DEL_REGION_FLAGS = (sublime.DRAW_EMPTY |
                        sublime.HIDE_ON_MINIMAP |
                        sublime.DRAW_EMPTY_AS_OVERWRITE |
                        sublime.DRAW_NO_FILL)
