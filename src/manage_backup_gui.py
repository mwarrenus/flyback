import gnome, gobject, gtk, gtk.glade, os, sys, tempfile, threading

import backup
import settings
import util


RUN_FROM_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))

  
def echo(*args):
  print 'echo', args

class GUI(object):

  def close(self, a=None, b=None):
    self.main_window.hide()
    self.unregister_gui(self)
    
  def update_revisions(self):
    revisions = backup.get_revisions(self.uuid, self.host, self.path)
    treeview_revisions_widget = self.xml.get_widget('treeview_revisions')
    treeview_revisions_model = treeview_revisions_widget.get_model()
    treeview_revisions_model.clear()
    for rev in revisions:
      s = '%s\n<i>%s</i>' % ( util.pango_escape(rev['date']), util.pango_escape(rev['author']) )
      treeview_revisions_model.append((s,rev['commit']))
      
  def update_files(self,a=None):
    treeview_files_model = self.xml.get_widget('treeview_files').get_model()
    treeview_files_model.clear()
    
    model, entry = a.get_selection().get_selected()
    if not entry:
      self.xml.get_widget('toolbutton_export').set_sensitive( False )
      self.xml.get_widget('toolbutton_explore').set_sensitive( False )
    else:
      self.xml.get_widget('toolbutton_export').set_sensitive( True )
      self.xml.get_widget('toolbutton_explore').set_sensitive( True )
      rev = entry and model.get_value(entry, 1)
      for fn in backup.get_files_for_revision(self.uuid, self.host, self.path, rev):
        treeview_files_model.append( (util.pango_escape(fn),) )
  
  def get_selected_revision(self):
    model, entry = self.xml.get_widget('treeview_revisions').get_selection().get_selected()
    if not entry: return
    rev = entry and model.get_value(entry, 1)
    return rev

  def start_backup(self):
    icon = self.main_window.render_icon(gtk.STOCK_SAVE, gtk.ICON_SIZE_MENU)
    running_tasks_model = self.xml.get_widget('running_tasks').get_model()
    i = running_tasks_model.append( ( icon, util.pango_escape('backing up: '+self.path) ) )
    gui = self
    
    class T(threading.Thread):
      def run(self):
        backup.backup(gui.uuid, gui.host, gui.path)
        gtk.gdk.threads_enter()
        gui.update_revisions()
        running_tasks_model.remove(i)
        gtk.gdk.threads_leave()
    T().start()
    
    
  def start_export(self):
    dialog = gtk.FileChooserDialog(title='Select folder to save archive to...', parent=None, action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK), backend=None)
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
      target_dir = dialog.get_filename()
      rev = self.get_selected_revision()

      icon = self.main_window.render_icon(gtk.STOCK_FLOPPY, gtk.ICON_SIZE_MENU)
      running_tasks_model = self.xml.get_widget('running_tasks').get_model()
      i = running_tasks_model.append( ( icon, util.pango_escape('exporting selected revision to: '+target_dir) ) )
      gui = self
      class T(threading.Thread):
        def run(self):
          fn = backup.export_revision( gui.uuid, gui.host, gui.path, rev, target_dir )
          util.open_file(fn)
          gtk.gdk.threads_enter()
          running_tasks_model.remove(i)
          gtk.gdk.threads_leave()
      T().start()
      
    elif response == gtk.RESPONSE_CANCEL:
      pass
    dialog.destroy()

  def start_explore(self):
    target_dir = tmp = tempfile.mkdtemp()
    rev = self.get_selected_revision()
    
    icon = self.main_window.render_icon(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
    running_tasks_model = self.xml.get_widget('running_tasks').get_model()
    i = running_tasks_model.append( ( icon, util.pango_escape('preparing folder for exploration: '+target_dir) ) )
    gui = self
    
    class T(threading.Thread):
      def run(self):
        fn = backup.export_revision( gui.uuid, gui.host, gui.path, rev, target_dir )
        os.chdir(target_dir)
        os.system('tar -zxvf "%s"' % fn)
        os.remove(fn)
        os.chdir(RUN_FROM_DIR)
        util.open_file(target_dir)
        gtk.gdk.threads_enter()
        running_tasks_model.remove(i)
        gtk.gdk.threads_leave()
    T().start()
    


  def __init__(self, register_gui, unregister_gui, uuid, host, path):

    self.register_gui = register_gui
    self.unregister_gui = unregister_gui
    self.uuid = uuid
    self.host = host
    self.path = path
  
    self.xml = gtk.glade.XML( os.path.join( RUN_FROM_DIR, 'glade', 'manage_backup.glade' ) )
    self.main_window = self.xml.get_widget('window')
    self.main_window.connect("delete-event", self.close )
    icon = self.main_window.render_icon(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_BUTTON)
    self.main_window.set_icon(icon)
    self.xml.get_widget('entry_drive_name').set_text( backup.get_drive_name(self.uuid) )
    self.xml.get_widget('entry_path').set_text( self.path )
    self.main_window.set_title('%s v%s - Manage Backup' % (settings.PROGRAM_NAME, settings.PROGRAM_VERSION))
    
    # toolbar
    self.xml.get_widget('toolbutton_backup').set_sensitive( backup.test_backup_assertions(self.uuid, self.host, self.path) )
    self.xml.get_widget('toolbutton_backup').connect('clicked', lambda x: self.start_backup() )
    self.xml.get_widget('toolbutton_export').connect('clicked', lambda x: self.start_export() )
    self.xml.get_widget('toolbutton_explore').connect('clicked', lambda x: self.start_explore() )
    
    # revision list
    treeview_revisions_model = gtk.ListStore( str, str )
    treeview_revisions_widget = self.xml.get_widget('treeview_revisions')
    renderer = gtk.CellRendererText()
    treeview_revisions_widget.append_column( gtk.TreeViewColumn('History', renderer, markup=0) )
    treeview_revisions_widget.set_model(treeview_revisions_model)
    treeview_revisions_widget.connect( 'cursor-changed', self.update_files )
    treeview_revisions_widget.connect( 'move-cursor', self.update_files )
    treeview_revisions_widget.set_property('rules-hint', True)
    self.update_revisions()
    
    # file list
    treeview_files_widget = self.xml.get_widget('treeview_files')
    treeview_files_model = gtk.ListStore( str )
    renderer = gtk.CellRendererText()
    renderer.set_property('font','monospace')
    treeview_files_widget.append_column( gtk.TreeViewColumn('Files', renderer, markup=0) )
    treeview_files_widget.set_model(treeview_files_model)
    treeview_files_widget.set_property('rules-hint', True)

    # task list
    running_tasks_widget = self.xml.get_widget('running_tasks')
    running_tasks_model = gtk.ListStore( gtk.gdk.Pixbuf, str )
    renderer = gtk.CellRendererPixbuf()
    renderer.set_property('xpad', 4)
    renderer.set_property('ypad', 4)
    running_tasks_widget.append_column( gtk.TreeViewColumn('', renderer, pixbuf=0) )
    renderer = gtk.CellRendererText()
    running_tasks_widget.append_column( gtk.TreeViewColumn('', renderer, markup=1) )
    running_tasks_widget.set_model(running_tasks_model)
    running_tasks_widget.set_headers_visible(False)

    self.main_window.show()
    


