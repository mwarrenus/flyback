import gnome, gobject, gtk, gtk.glade, os, sys, tempfile, threading

import backup
import settings
import util

RUN_FROM_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))


class GUI(object):

  def close(self, a=None, b=None):
    self.main_window.hide()
    self.unregister_gui(self)
  
  def save(self, a=None):
    backup.save_preferences(self.uuid, self.host, self.path, self.preferences)
    self.close()
    
  def toggled(self, button):
    name = button.get_name()
    assert name.startswith('checkbutton_')
    preference = name[ name.index('_')+1: ]
    self.preferences[preference] = button.get_active()
    print 'toggled:', preference, button.get_active()
  
  def __init__(self, register_gui, unregister_gui, uuid, host, path):

    self.register_gui = register_gui
    self.unregister_gui = unregister_gui
    self.uuid = uuid
    self.host = host
    self.path = path
  
    self.xml = gtk.glade.XML( os.path.join( RUN_FROM_DIR, 'glade', 'manage_backup_preferences.glade' ) )
    self.main_window = self.xml.get_widget('dialog')
    self.xml.get_widget('button_cancel').connect('clicked', self.close)
    self.xml.get_widget('button_ok').connect('clicked', self.save)
    icon = self.main_window.render_icon(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_BUTTON)
    self.main_window.set_icon(icon)
    self.main_window.set_title('%s v%s - Backup Preferences' % (settings.PROGRAM_NAME, settings.PROGRAM_VERSION))
    
    self.preferences = backup.get_preferences(self.uuid, self.host, self.path)

    self.xml.get_widget('checkbutton_exclude_audio').set_active(self.preferences.get('exclude_audio'))
    self.xml.get_widget('checkbutton_exclude_video').set_active(self.preferences.get('exclude_video'))
    self.xml.get_widget('checkbutton_exclude_trash').set_active(self.preferences.get('exclude_trash'))
    self.xml.get_widget('checkbutton_exclude_cache').set_active(self.preferences.get('exclude_cache'))
    self.xml.get_widget('checkbutton_exclude_vms').set_active(self.preferences.get('exclude_vms'))
    self.xml.get_widget('checkbutton_exclude_iso').set_active(self.preferences.get('exclude_iso'))

    self.xml.get_widget('checkbutton_exclude_audio').connect('toggled', self.toggled)
    self.xml.get_widget('checkbutton_exclude_video').connect('toggled', self.toggled)
    self.xml.get_widget('checkbutton_exclude_trash').connect('toggled', self.toggled)
    self.xml.get_widget('checkbutton_exclude_cache').connect('toggled', self.toggled)
    self.xml.get_widget('checkbutton_exclude_vms').connect('toggled', self.toggled)
    self.xml.get_widget('checkbutton_exclude_iso').connect('toggled', self.toggled)
    
    self.main_window.show()
    

