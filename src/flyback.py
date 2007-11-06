import os
import dircache
import desktop
import gconf
import pickle
from datetime import datetime
from time import strptime

try:
     import pygtk
     pygtk.require("2.0")
except:
      pass
try:
    import gtk
    import gtk.glade
    import gnome.ui   
    import gobject
except:
    sys.exit(1)


client = gconf.client_get_default()
client.add_dir ("/apps/flyback", gconf.CLIENT_PRELOAD_NONE)


class backup:
    
    parent_backup_dir = None

    def get_available_backups(self):
        self.parent_backup_dir = client.get_string("/apps/flyback/external_storage_location")
        print 'self.parent_backup_dir', self.parent_backup_dir
        try:
            dirs = dircache.listdir(self.parent_backup_dir)
            dir_datetimes = []
            for dir in dirs:
                dir_datetimes.append( datetime(*strptime(dir, "%Y-%m-%d %H:%M:%S")[0:6]) )
            dir_datetimes.sort(reverse=True)
            return dir_datetimes
        except:
            return []
        
    
    def get_latest_backup_dir(self):
        try:
            return get_available_backups()[0]
        except:
            return None
            
    def backup(self):
        print 'parent_backup_dir', self.parent_backup_dir
        latest_backup_dir = self.get_latest_backup_dir()
        s = client.get_string("/apps/flyback/included_dirs")
        if s:
            self.dirs_to_backup = pickle.loads(s)
        print 'dirs_to_backup', self.dirs_to_backup
        new_backup = self.parent_backup_dir +'/'+ datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if latest_backup_dir:
            last_backup = self.parent_backup_dir +'/'+ latest_backup_dir.strftime("%Y-%m-%d %H:%M:%S")
            for dir in self.dirs_to_backup:
                os.system("mkdir -p '%s'" % new_backup + dir)
                os.system("rsync -av --delete --link-dest='%s' '%s/' '%s/'" % (last_backup + dir, dir, new_backup + dir))
        else:
            for dir in self.dirs_to_backup:
                os.system("mkdir -p '%s'" % new_backup + dir)
                os.system("rsync -av --delete '%s/' '%s/'" % (dir, new_backup + dir))
        os.system(" chmod -R -w '%s'" % new_backup)


class main_gui:
    
    xml = None
    selected_backup = None
    backup = backup()
    cur_dir = '/'
    available_backup_list = gtk.ListStore(gobject.TYPE_STRING)
    file_list = gtk.ListStore(gobject.TYPE_STRING)
        
    def select_subdir(self, treeview, o1, o2):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()
        new_file = self.cur_dir.rstrip('/') +'/'+ liststore[rows[0]][0].rstrip('/')
        if os.path.isdir(new_file):
            self.cur_dir = new_file
        else:
            print 'not a dir:', new_file
            desktop.open(new_file)
        self.xml.get_widget('location_field').set_current_folder(self.cur_dir)
        self.refresh_file_list()

    def go_home(self, o):
        self.cur_dir = os.path.expanduser("~")
        self.xml.get_widget('location_field').set_current_folder(self.cur_dir)
        self.refresh_file_list()

    def select_pardir(self, o):
        self.cur_dir = ('/'.join(self.cur_dir.split('/')[:-1]))
        if not self.cur_dir: self.cur_dir = '/'
        self.xml.get_widget('location_field').set_current_folder(self.cur_dir)
        self.refresh_file_list()

    def select_dir(self, o):
        new_file = o.get_current_folder()
        if os.path.isdir(new_file):
            self.cur_dir = new_file
        else:
            print 'not a dir:', new_file
            desktop.open(new_file)
        self.refresh_file_list()

    def select_backup(self, treeview):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()
        self.selected_backup = liststore[rows[0]][0]
        if self.selected_backup=='now':
            self.selected_backup = None
            self.xml.get_widget('restore_button').set_sensitive(False)
        else:
            #self.xml.get_widget('restore_button').set_sensitive(True)
            pass
        self.refresh_file_list()
        
    def run_backup(self, o):
        self.xml.get_widget('progressbar').pulse()
        self.backup.backup()
        self.refresh_available_backup_list()
        
    def refresh_all(self, o):
        self.refresh_available_backup_list()
        self.refresh_file_list()
        
    def refresh_available_backup_list(self):
        self.available_backup_list.clear()
        self.available_backup_list.append( ('now',) )
        for n in self.backup.get_available_backups():
            self.available_backup_list.append( (n,) )
            
    def refresh_file_list(self):
        self.xml.get_widget('pardir_button').set_sensitive( self.cur_dir != '/' )
        self.file_list.clear()
        if self.selected_backup:
            focus_dir = self.backup.parent_backup_dir +'/'+ self.selected_backup + self.cur_dir
        else:
            focus_dir = self.cur_dir
        print 'focus_dir', focus_dir
        try:
            dirs = dircache.listdir(focus_dir)
            #dircache.annotate('/', dirs)
            for dir in dirs:
                self.file_list.append((dir,))
        except:
            pass
        
    def show_about_dialog(self, o):
        self.xml.get_widget('about_dialog').show()
    
    def hide_about_dialog(self, o):
        self.xml.get_widget('about_dialog').show()
    
    def show_prefs_dialog(self, o):
        prefs_gui(self)
    
    def __init__(self):
        
        gnome.init("programname", "version")
        self.xml = gtk.glade.XML('viewer.glade')
        
        # bind the window close event
        self.xml.get_widget('window1').connect("destroy", gtk.main_quit)
        self.xml.get_widget('about_dialog').connect("close", self.hide_about_dialog)
    
        # build the model for the available backups list
        self.refresh_available_backup_list()
        # and bind it to the treeview
        available_backup_list_widget = self.xml.get_widget('available_backup_list')
        available_backup_list_widget.set_model(self.available_backup_list)
        available_backup_list_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("system snapshots", renderer, text=0)
        num = available_backup_list_widget.append_column(column)
        # and add its handlers
        available_backup_list_widget.connect('cursor-changed', self.select_backup)
        
        # build the model for the file list
        self.refresh_file_list()
        # and bind it to the treeview
        file_list_widget = self.xml.get_widget('file_list')
        file_list_widget.set_model(self.file_list)
        file_list_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("file", renderer, text=0)
        num = file_list_widget.append_column(column)
        # and add its handlers
        file_list_widget.connect('row-activated', self.select_subdir)

        # bind toolbar functions
        self.xml.get_widget('backup_button').connect('clicked', self.run_backup)
        self.xml.get_widget('refresh_button').connect('clicked', self.refresh_all)
        self.xml.get_widget('pardir_button').connect('clicked', self.select_pardir)
        self.xml.get_widget('home_button').connect('clicked', self.go_home)
        self.xml.get_widget('location_field').connect('current-folder-changed', self.select_dir)
        
        # bind menu functions
        self.xml.get_widget('menuitem_about').connect('activate', self.show_about_dialog)
        self.xml.get_widget('menuitem_prefs').connect('activate', self.show_prefs_dialog)
        self.xml.get_widget('menuitem_quit').connect('activate', gtk.main_quit)
        
        self.xml.get_widget('location_field').set_current_folder(self.cur_dir)


class prefs_gui:
    
    xml = None
    main_gui = None
    
    included_dirs = []
    included_dirs_liststore = gtk.ListStore(gobject.TYPE_STRING)
    
    def hide_prefs_dialog(self, o):
        print 'woot'
        self.xml.get_widget('prefs_dialog').hide()
        
    def save_prefs(self, o):
        client.set_string ("/apps/flyback/external_storage_location", self.xml.get_widget('external_storage_location').get_current_folder() )
        client.set_string ("/apps/flyback/included_dirs", pickle.dumps(self.included_dirs) )
        self.xml.get_widget('prefs_dialog').hide()
        self.main_gui.refresh_available_backup_list()
        
    def add_include_dir(self, o):
            new_dir =  self.xml.get_widget('include_dir_filechooser').get_current_folder()
            if new_dir not in self.included_dirs:
                self.included_dirs.append(new_dir)
                self.included_dirs.sort()
                self.refresh_included_dirs_list()

    def refresh_included_dirs_list(self):
        self.included_dirs_liststore.clear()
        for n in self.included_dirs:
            self.included_dirs_liststore.append( (n,) )
            
    def include_dir_key_press(self, treeview, o2):
        if o2.keyval==gtk.keysyms.Delete:
            print 'woot!!!'
            selection = treeview.get_selection()
            liststore, rows = selection.get_selected_rows()
            self.included_dirs.remove( liststore[rows[0]][0] )
            self.refresh_included_dirs_list()

    def __init__(self, o):
        self.xml = o.xml
        self.main_gui = o
        
        s = client.get_string("/apps/flyback/included_dirs")
        print s
        if s:
            self.included_dirs = pickle.loads(s)
        
        # bind ok/cancel buttons
        self.xml.get_widget('prefs_dialog_ok').connect('clicked', self.save_prefs)
        self.xml.get_widget('prefs_dialog_cancel').connect('clicked', self.hide_prefs_dialog)

        # bind include/exclude dir buttons
        self.xml.get_widget('include_dir_add_button').connect('clicked', self.add_include_dir)
        self.xml.get_widget('dirs_include').connect('key-press-event', self.include_dir_key_press)

        # build include/exclude lists
        dirs_includet_widget = self.xml.get_widget('dirs_include')
        dirs_includet_widget.set_model(self.included_dirs_liststore)
        dirs_includet_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("included dirs", renderer, text=0)
        if not dirs_includet_widget.get_columns():
            dirs_includet_widget.append_column(column)
        self.refresh_included_dirs_list()

        # init external_storage_location
        external_storage_location = client.get_string("/apps/flyback/external_storage_location")
        if not external_storage_location:
            external_storage_location = '/backups'
        self.xml.get_widget('external_storage_location').set_current_folder( external_storage_location )

        
        self.xml.get_widget('prefs_dialog').show()

        
    
if __name__ == "__main__":
    main_gui()
    gtk.main()


