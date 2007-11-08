#!/usr/bin/env python

#    FlyBack
#    Copyright (C) 2007 Derek Anderson
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

VERSION = 'v0.2.1'
GPL = open( 'GPL.txt', 'r' ).read()

import os
import dircache
import desktop
import gconf
import pickle
from datetime import datetime
from time import strptime
import threading

try:
     import pygtk
     pygtk.require("2.0")
except:
      pass
try:
    import gobject, gtk
    import gtk.glade
    import gnome.ui   
    import gobject
except:
    sys.exit(1)


gobject.threads_init()
gtk.gdk.threads_init()

client = gconf.client_get_default()
client.add_dir ("/apps/flyback", gconf.CLIENT_PRELOAD_NONE)


class backup:
    
    xml = None
    main_gui = None
    parent_backup_dir = None
    dirs_to_backup = []

    def __init__(self, o):
        self.xml = o.xml
        self.main_gui = o

    def get_available_backups(self):
        self.parent_backup_dir = client.get_string("/apps/flyback/external_storage_location")
        if not self.parent_backup_dir:
#            error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
#            error.set_markup('Please select an external storage location in the preferences window.')
#            error.show()
            return []
        try:
            dirs = dircache.listdir(self.parent_backup_dir)
            dir_datetimes = []
            for dir in dirs:
                dir_datetimes.append( datetime(*strptime(dir, "%Y-%m-%d %H:%M:%S")[0:6]) )
            dir_datetimes.sort(reverse=True)
            return dir_datetimes
        except:
            print 'error2'
            return []
        
    def get_latest_backup_dir(self):
        try:
            return self.get_available_backups()[0]
        except:
            return None
    
    def get_backup_command(self, latest_backup_dir, dir, new_backup):
        if latest_backup_dir:
            last_backup = self.parent_backup_dir +'/'+ latest_backup_dir.strftime("%Y-%m-%d %H:%M:%S")
            return "rsync -av --delete --link-dest='%s' '%s/' '%s/'" % (last_backup + dir, dir, new_backup + dir)
        else:
            return "rsync -av --delete '%s/' '%s/'" % (dir, new_backup + dir)
    
    def run_cmd_output_gui(self, cmd):
        text_view = self.xml.get_widget('backup_output_text')
        text_buffer = text_view.get_buffer()
        output = []

        gtk.gdk.threads_enter()
        text_buffer.insert( text_buffer.get_end_iter(), '$ '+ cmd +'\n' )
        gtk.gdk.threads_leave()
        stdin, stdout = os.popen4(cmd)
        for line in stdout:
            output.append(line)
            gtk.gdk.threads_enter()
            text_buffer.insert( text_buffer.get_end_iter(), line )
            text_view.scroll_to_mark(text_buffer.get_insert(), 0.1)
            gtk.gdk.threads_leave()
        gtk.gdk.threads_enter()
        text_buffer.insert( text_buffer.get_end_iter(), '\n' )
        gtk.gdk.threads_leave()
        stdin.close()
        stdout.close()
        return output
            
    def backup(self):
        backup_button = self.xml.get_widget('backup_button')
        latest_backup_dir = self.get_latest_backup_dir()
        s = client.get_string("/apps/flyback/included_dirs")
        if s:
            self.dirs_to_backup = pickle.loads(s)
        
        if not self.dirs_to_backup:
            error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
            error.connect('response', lambda x,y: error.destroy())
            error.set_markup('No directories set to backup.  Please add something to the "included dirs" list in the preferences window.')
            error.show()

        new_backup = self.parent_backup_dir +'/'+ datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        gtk.gdk.threads_enter()
        backup_button.set_label('Backup is running...')
        backup_button.set_sensitive(False)
        text_view = self.xml.get_widget('backup_output_text')
        text_buffer = text_view.get_buffer()
        text_buffer.delete( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
        gtk.gdk.threads_leave()
        
        for dir in self.dirs_to_backup:
            self.run_cmd_output_gui("mkdir -p '%s'" % new_backup + dir)
            cmd = self.get_backup_command(latest_backup_dir, dir, new_backup)
            self.run_cmd_output_gui(cmd)
        self.run_cmd_output_gui(" chmod -R -w '%s'" % new_backup)
        
        gtk.gdk.threads_enter()
        self.main_gui.refresh_available_backup_list()
        backup_button.set_label('Backup')
        backup_button.set_sensitive(True)
        gtk.gdk.threads_leave()

    def restore(self):
        restore_button = self.xml.get_widget('restore_button')

        src = self.parent_backup_dir +'/'+ self.main_gui.selected_backup + self.main_gui.cur_dir
#        print 'src', src
        dest = self.main_gui.cur_dir
#        print 'dest', dest
        model, all_selected = self.xml.get_widget('file_list').get_selection().get_selected_rows()
#        print 'model', model

        if not all_selected:
            error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
            error.connect('response', lambda x,y: error.destroy())
            error.set_markup('<b>No files selected to restore</b>\n\nPlease select something from the file list.')
            error.show()
            return
        
        gtk.gdk.threads_enter()
        restore_button.set_label('Restore is running...')
        restore_button.set_sensitive(False)
        text_view = self.xml.get_widget('backup_output_text')
        text_buffer = text_view.get_buffer()
        text_buffer.delete( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
        gtk.gdk.threads_leave()
        
        if not os.path.isdir(dest):
            cmd = "mkdir -p '%s'" % dest
            self.run_cmd_output_gui(cmd)
            gtk.gdk.threads_enter()
            text_buffer.insert( text_buffer.get_end_iter(), cmd +'\n' )
            text_view.scroll_to_mark(text_buffer.get_insert(), 0.1)
            gtk.gdk.threads_leave()

        for selected in all_selected:
            print 'selected', selected
            print 'model.get', model.get( model.get_iter(selected), 0)
            local_file = model.get( model.get_iter(selected), 0)[0]
            file = src +'/'+ local_file
            print 'file', file
            if os.path.isdir(file):
                cmd = 'cp -R "%s" "%s"' % (file, dest)
            else:
                cmd = 'cp "%s" "%s"' % (file, dest)
            self.run_cmd_output_gui(cmd)
            dest_file = self.main_gui.cur_dir +'/'+ local_file
            if os.path.isdir(file):
                cmd = 'chmod -R u+w "%s"' % dest_file
            else:
                cmd = 'chmod u+w "%s"' % dest_file
            self.run_cmd_output_gui(cmd)
            
        gtk.gdk.threads_enter()
        restore_button.set_label('Restore')
        restore_button.set_sensitive(True)
        gtk.gdk.threads_leave()
        

class main_gui:
    
    xml = None
    selected_backup = None
    backup = None
    cur_dir = '/'
    available_backup_list = gtk.ListStore(gobject.TYPE_STRING)
    file_list = gtk.ListStore(gobject.TYPE_STRING)
    backup_thread = None
    restore_thread = None
        
    def select_subdir(self, treeview, o1, o2):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()

        if self.selected_backup:
            focus_dir = self.backup.parent_backup_dir +'/'+ self.selected_backup + self.cur_dir
        else:
            focus_dir = self.cur_dir
        print 'focus_dir', focus_dir
        
        local_file = liststore[rows[0]][0].rstrip('/')
        
        new_file = focus_dir.rstrip('/') +'/'+ local_file
        print 'new_file', new_file
        if os.path.isdir(new_file):
            self.cur_dir = self.cur_dir.rstrip('/') +'/'+ local_file
            self.xml.get_widget('location_field').set_text(self.cur_dir)
        else:
            print 'not a dir:', new_file
            desktop.open(new_file)
        self.refresh_file_list()

    def go_home(self, o):
        self.cur_dir = os.path.expanduser("~")
        self.xml.get_widget('location_field').set_current_folder(self.cur_dir)
        self.refresh_file_list()

    def select_pardir(self, o):
        self.cur_dir = ('/'.join(self.cur_dir.split('/')[:-1]))
        if not self.cur_dir: self.cur_dir = '/'
        self.xml.get_widget('location_field').set_text(self.cur_dir)
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
            self.xml.get_widget('restore_button').set_sensitive(True)
            pass
        self.refresh_file_list()
        
    def run_backup(self, o):
        self.backup_thread = threading.Thread(target= self.backup.backup)
        self.backup_thread.start()
        
    def run_restore(self, o):
        print o
        self.restore_thread = threading.Thread(target= self.backup.restore)
        self.restore_thread.start()
        
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
        try:
            dirs = dircache.listdir(focus_dir)
            #dircache.annotate('/', dirs)
            for dir in dirs:
                self.file_list.append((dir,))
        except:
            pass
        
    def show_about_dialog(self, o):
        about = gtk.AboutDialog()
        about.set_name('FlyBack')
        about.set_version(VERSION)
        about.set_copyright('Copyright (c) 2007 Derek Anderson')
        about.set_comments('''FlyBack is a backup and recovery tool loosely modeled after Apple's new "Time Machine".''')
        about.set_license(GPL)
        about.set_website('http://code.google.com/p/flyback/')
        about.set_authors(['Derek Anderson','http://kered.org'])
        about.connect('response', lambda x,y: about.destroy())
        about.show()
    
    def hide_window(self, window, o2):
        window.hide()
        return True
    
    def check_if_safe_to_quit(self, w, o):
            if self.backup_thread and self.backup_thread.isAlive():
                error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
                error.set_markup("""<b>Backup Running</b>\n\nA backup is currently running...\nPlease wait for it to finish before exiting.""")
                error.connect('response', lambda x,y: error.destroy())
                error.show()
                return True
            elif self.restore_thread and self.restore_thread.isAlive():
                error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
                error.set_markup("""<b>Restore Running</b>\n\nA restore is currently running...\nPlease wait for it to finish before exiting.""")
                error.connect('response', lambda x,y: error.destroy())
                error.show()
                return True
            else:
                gtk.main_quit()
                
    def show_hide_output(self, o):
        if o.get_active():
            self.xml.get_widget('scrolledwindow_backup_output').show()
        else:
            self.xml.get_widget('scrolledwindow_backup_output').hide()
        client.set_bool("/apps/flyback/show_output", o.get_active())
    
    def __init__(self):
        
        gnome.init("programname", "version")
        self.xml = gtk.glade.XML('viewer.glade')
        o = self
        self.backup = backup(o)
        
        # bind the window events
        main_window = self.xml.get_widget('window1')
        main_window.connect("delete-event", self.check_if_safe_to_quit )
        icon = main_window.render_icon(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_BUTTON)
        main_window.set_icon(icon)
        self.xml.get_widget('prefs_dialog').connect("delete-event", self.hide_window)
    
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
        file_list_widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("file", renderer, text=0)
        num = file_list_widget.append_column(column)
        # and add its handlers
        file_list_widget.connect('row-activated', self.select_subdir)

        # bind toolbar functions
        self.xml.get_widget('backup_button').connect('clicked', self.run_backup)
        self.xml.get_widget('restore_button').connect('clicked', self.run_restore)
        self.xml.get_widget('refresh_button').connect('clicked', self.refresh_all)
        self.xml.get_widget('pardir_button').connect('clicked', self.select_pardir)
        self.xml.get_widget('home_button').connect('clicked', self.go_home)
        # self.xml.get_widget('location_field').connect('current-folder-changed', self.select_dir)
        
        # bind menu functions
        self.xml.get_widget('menuitem_about').connect('activate', self.show_about_dialog)
        self.xml.get_widget('menuitem_prefs').connect('activate', lambda w: prefs_gui(self) )
        self.xml.get_widget('menuitem_quit').connect('activate', gtk.main_quit)
        menuitem_show_output = self.xml.get_widget('menuitem_show_output')
        menuitem_show_output.connect('activate', self.show_hide_output )
        menuitem_show_output.set_active(client.get_bool("/apps/flyback/show_output"))
        self.show_hide_output(menuitem_show_output)
        
        # set current folder
        self.xml.get_widget('location_field').set_text(self.cur_dir)
        
        main_window.show()
        
        # if no external storage defined, show prefs
        if not client.get_string("/apps/flyback/external_storage_location"):
            prefs_gui(self)


class prefs_gui:
    
    xml = None
    main_gui = None
    
    included_dirs = []
    included_dirs_liststore = gtk.ListStore(gobject.TYPE_STRING)
    excluded_dirs = []
    excluded_dirs_liststore = gtk.ListStore(gobject.TYPE_STRING)
            
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

    def add_exclude_dir(self, o):
            new_dir =  self.xml.get_widget('exclude_dir_filechooser').get_current_folder()
            if new_dir not in self.excluded_dirs:
                self.excluded_dirs.append(new_dir)
                self.excluded_dirs.sort()
                self.refresh_excluded_dirs_list()

    def refresh_excluded_dirs_list(self):
        self.excluded_dirs_liststore.clear()
        for n in self.excluded_dirs:
            self.excluded_dirs_liststore.append( (n,) )
            
    def exclude_dir_key_press(self, treeview, o2):
        if o2.keyval==gtk.keysyms.Delete:
            print 'woot!!!'
            selection = treeview.get_selection()
            liststore, rows = selection.get_selected_rows()
            self.excluded_dirs.remove( liststore[rows[0]][0] )
            self.refresh_excluded_dirs_list()

    def __init__(self, o):
        self.xml = o.xml
        self.main_gui = o
        
        s = client.get_string("/apps/flyback/included_dirs")
        if s:
            self.included_dirs = pickle.loads(s)
        s = client.get_string("/apps/flyback/excluded_dirs")
        if s:
            self.excluded_dirs = pickle.loads(s)
        
        # bind ok/cancel buttons
        self.xml.get_widget('prefs_dialog_ok').connect('clicked', self.save_prefs)
        self.xml.get_widget('prefs_dialog_cancel').connect('clicked', lambda w: self.xml.get_widget('prefs_dialog').hide() )

        # bind include/exclude dir buttons
        self.xml.get_widget('include_dir_add_button').connect('clicked', self.add_include_dir)
        self.xml.get_widget('dirs_include').connect('key-press-event', self.include_dir_key_press)
        self.xml.get_widget('exclude_dir_add_button').connect('clicked', self.add_exclude_dir)
        self.xml.get_widget('dirs_exclude').connect('key-press-event', self.exclude_dir_key_press)

        # build include/exclude lists
        dirs_includet_widget = self.xml.get_widget('dirs_include')
        dirs_includet_widget.set_model(self.included_dirs_liststore)
        dirs_includet_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("included dirs", renderer, text=0)
        if not dirs_includet_widget.get_columns():
            dirs_includet_widget.append_column(column)
        self.refresh_included_dirs_list()
        dirs_excludet_widget = self.xml.get_widget('dirs_exclude')
        dirs_excludet_widget.set_model(self.excluded_dirs_liststore)
        dirs_excludet_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("excluded dirs", renderer, text=0)
        if not dirs_excludet_widget.get_columns():
            dirs_excludet_widget.append_column(column)
        self.refresh_excluded_dirs_list()

        # init external_storage_location
        external_storage_location = client.get_string("/apps/flyback/external_storage_location")
        if not external_storage_location:
            external_storage_location = '/external_storage_location'
        self.xml.get_widget('external_storage_location').set_current_folder( external_storage_location )

        
        self.xml.get_widget('prefs_dialog').show()

        
    
if __name__ == "__main__":
    main_gui()
    gtk.main()


