class SwitchProxy(object):
    def __init__(self, manager, switch):
        self._switch = switch
        self._manager = manager

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self._switch, attr)

    def __setattr__(self, attr, value):
        if attr in ('_switch', '_manager'):
            object.__setattr__(self, attr, value)
        else:
            setattr(self._switch, attr, value)

    def _clear(self):
        key = self._switch.key
        if key in self._manager:
            del self._manager[key]

    def delete(self):
        self._clear()
        self._switch.m.delete()

    def save(self):
        self._clear()
        self._switch.m.save()

    def add_condition(self, *args, **kwargs):
        self._clear()
        return self._switch.add_condition(self._manager, *args, **kwargs)

    def remove_condition(self, *args, **kwargs):
        self._clear()
        return self._switch.remove_condition(self._manager, *args, **kwargs)

    def clear_conditions(self, *args, **kwargs):
        self._clear()
        return self._switch.clear_conditions(self._manager, *args, **kwargs)

    def get_active_conditions(self, *args, **kwargs):
        return self._switch.get_active_conditions(self._manager, *args, **kwargs)
