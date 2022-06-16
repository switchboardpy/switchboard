from blinker import signal

#: This signal is sent when a switch is added.
#:
#: Example subscriber::
#:
#:      def switch_added_callback(switch):
#:          logging.debug('Switch was added: %r', switch.label)
#:
#:      from switchboard.signals import switch_added
#:      switch_added.connect(switch_added_callback)
switch_added = signal('switch_added')

#: This signal is sent when a switch is deleted.
#:
#: Example subscriber::
#:
#:      def switch_deleted_callback(result):
#:          if result['ok']:
#:              logging.debug('Switch was deleted')
#:
#:      from switchboard.signals import switch_deleted
#:      switch_deleted.connect(switch_deleted_callback)
switch_deleted = signal('switch_deleted')

#: This signal is sent when a switch is updated.
#:
#: Example subscriber::
#:
#:      def switch_updated_callback(result):
#:          if result['ok']:
#:              logging.debug('Switch was updated')
#:
#:      from switchboard.signals import switch_updated
#:      switch_updated.connect(switch_updated_callback)
switch_updated = signal('switch_updated')

#: This signal is sent when the status on a switch changes.
#:
#: Example subscriber::
#:
#:      def switch_status_updated_callback(switch):
#:          logging.debug('Switch has updated status: %r; %r', switch.label, switch.status)
#:
#:      from switchboard.signals import switch_status_updated
#:      switch_status_updated.connect(switch_status_updated_callback)
switch_status_updated = signal('switch_status_updated')

#: This signal is sent when a condition is added to the switch.
#:
#: Example subscriber::
#:
#:      def switch_condition_added_callback(switch):
#:          logging.debug('Switch has a new condition: %r', switch.label)
#:
#:      from switchboard.signals import switch_condition_added
#:      switch_condition_added.connect(switch_condition_added_callback)
switch_condition_added = signal('switch_condition_added')

#: This signal is sent when a condition is removed from the switch.
#:
#: Example subscriber::
#:
#:      def switch_condition_removed_callback(switch):
#:          logging.debug('Switch has deleted a condition: %r', switch.label)
#:
#:      from switchboard.signals import switch_condition_removed
#:      switch_condition_removed.connect(switch_condition_removed_callback)
switch_condition_removed = signal('switch_condition_removed')

#: This signal provides an easy, standard way for various frameworks to notify
#: Switchboard that a request has finished
request_finished = signal('request_finished')
