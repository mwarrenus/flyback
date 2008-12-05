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

import os, sys, traceback, math

from common import *




import commands, dircache, pwd
import desktop
from datetime import datetime
from time import strptime
import threading
import help_data
import config_backend
import getopt
import prefs, history


client = config_backend.GConfConfig()

from backup_backend import *


    
    
class MainGUI:
    
    xml = None
    selected_backup = None
    backup = None
    cur_dir = '/'
    available_backups = []
    available_backup_list = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
    file_list = gtk.ListStore( str, str, str, bool, gtk.gdk.Pixbuf )
    backup_thread = None
    restore_thread = None
        
    def select_subdir(self, treeview, o1, o2):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()

        focus_dir = self.get_focus_dir()
#        print 'focus_dir', focus_dir
        
        local_file = liststore[rows[0]][0].rstrip('/')
        
        new_file = focus_dir.rstrip('/') +'/'+ local_file
#        print 'new_file', new_file
        if os.path.isdir(new_file):
            self.cur_dir = self.cur_dir.rstrip('/') +'/'+ local_file
            self.xml.get_widget('location_field').set_text(self.cur_dir)
        else:
            print 'not a dir:', new_file
            desktop.open(new_file)
        self.refresh_file_list()

    def go_home(self, o):
        self.cur_dir = os.path.expanduser("~")
        self.xml.get_widget('location_field').set_text(self.cur_dir)
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
        self.selected_backup = liststore[rows[0]][1]
        self.xml.get_widget('restore_button').set_sensitive( bool(self.selected_backup) )
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
        self.available_backups = self.backup.get_available_backups()
        self.available_backup_list.clear()
        self.available_backup_list.append( ('now',None) )
        for n in self.available_backups:
            adjusted_for_tz = n + get_tz_offset()
            self.available_backup_list.append( (adjusted_for_tz,n) )
            
    def get_focus_dir(self):
        if self.selected_backup:
            return self.backup.parent_backup_dir +'/'+ self.selected_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
        else:
            return self.cur_dir

    
    def refresh_file_list(self):
        pardir_button = self.xml.get_widget('pardir_button')
        pardir_button.set_sensitive( self.cur_dir != '/' )
        self.file_list.clear()
        previous_focus_dir = None
        previous_backup = None
        show_hidden_files = client.get_bool("/apps/flyback/show_hidden_files")
        sort_dirs_first = client.get_bool("/apps/flyback/sort_dirs_first")
        if self.selected_backup:
            focus_dir = self.backup.parent_backup_dir +'/'+ self.selected_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
            i = self.available_backups.index(self.selected_backup)
            if i<len(self.available_backups)-1:
                previous_backup = self.available_backups[i+1]
                previous_focus_dir = self.backup.parent_backup_dir +'/'+ previous_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
        else:
            if self.available_backups:
                previous_backup = self.available_backups[0]
                previous_focus_dir = self.backup.parent_backup_dir +'/'+ previous_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
            focus_dir = self.cur_dir
#        print 'previous_backup, previous_focus_dir', previous_backup, previous_focus_dir
        if True:
#        try:
            try:
                files = os.listdir(focus_dir)
            except:
                self.select_pardir(None)
                return
            
            files.sort()
            if sort_dirs_first:
                dirs = []
                not_dirs = []
                for file in files:
                    if os.path.isdir( os.path.join( focus_dir, file ) ):
                        dirs.append(file)
                    else:
                        not_dirs.append(file)
                files = dirs
                files.extend(not_dirs)
            for file in files:
                full_file_name = os.path.join( focus_dir, file )
                file_stats = os.stat(full_file_name)
                color = False
#                print 'full_file_name', full_file_name
#                print 'file_stats', file_stats
                if previous_focus_dir:
                    previous_full_file_name = os.path.join( previous_focus_dir, file )
                    if os.path.isfile(previous_full_file_name):
#                        print 'previous_full_file_name', previous_full_file_name
                        previous_file_stats = os.stat(previous_full_file_name)
#                        print 'previous_file_stats', previous_file_stats
                        if self.selected_backup:
                            if file_stats[1]!=previous_file_stats[1]:
                                color = True
                        else:
                            if file_stats[8]!=previous_file_stats[8]:
                                color = True
                    else:
                        if not os.path.isdir(previous_full_file_name):
                            color = True
                try:
                    if os.path.isdir(full_file_name):
                        size = humanize_count( len(os.listdir(full_file_name)), 'item', 'items' )
                        icon = self.xml.get_widget('home_button').render_icon(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
#                        color = False
                    else:
                        size = humanize_bytes(file_stats[6])
                        icon = self.xml.get_widget('home_button').render_icon(gtk.STOCK_FILE, gtk.ICON_SIZE_MENU)
                except:
                    size = ''
                    icon = self.xml.get_widget('home_button').render_icon(gtk.STOCK_FILE, gtk.ICON_SIZE_MENU)
                if show_hidden_files or not file.startswith('.'):
                    self.file_list.append(( file, size, datetime.fromtimestamp(file_stats[8]), color, icon ))
#        except:
#            traceback.print_stack()
        
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
        
    def show_hide_opengl(self, o):
        if o.get_active():
            self.xml.get_widget("window_opengl").show_all()
        else:
            self.xml.get_widget("window_opengl").hide()
        client.set_bool("/apps/flyback/show_opengl", o.get_active())
    
    def file_list_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                menu = gtk.Menu()
                open = gtk.ImageMenuItem(stock_id=gtk.STOCK_OPEN)
#                open.set_image( gtk.image_new_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_MENU) )
                open.connect( 'activate', lambda x: self.select_subdir(self.xml.get_widget('file_list'), None, None) )
                menu.append(open)
                folder = gtk.ImageMenuItem(stock_id='Open Containing _Folder')
                folder.set_image( gtk.image_new_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU) )
                folder.connect( 'activate', lambda x: desktop.open(self.get_focus_dir()) )
                menu.append(folder)
                restore = gtk.ImageMenuItem(stock_id="_Restore this Version")
                restore.set_image( gtk.image_new_from_stock(gtk.STOCK_REVERT_TO_SAVED, gtk.ICON_SIZE_MENU) )
                restore.set_sensitive( bool(self.selected_backup) )
                restore.connect( 'activate', self.run_restore )
                menu.append(restore)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.get_time())
            return True
        return False
   
    def __init__(self):
        
        gnome.init("programname", "version")
        self.xml = gtk.glade.XML(RUN_FROM_DIR + 'viewer.glade')
        o = self
        self.backup = backup(o)
        
        # bind the window events
        main_window = self.xml.get_widget('window1')
        main_window.connect("delete-event", self.check_if_safe_to_quit )
        icon = main_window.render_icon(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_BUTTON)
        main_window.set_icon(icon)
        self.xml.get_widget('prefs_dialog').connect("delete-event", self.hide_window)
        self.xml.get_widget('help_window').connect("delete-event", self.hide_window)
        self.xml.get_widget('window_opengl').connect("delete-event", self.hide_window)
        self.xml.get_widget('history_dialog').connect("delete-event", self.hide_window)
    
        # init opengl frontend
#        main.show_all()

        # build the model for the available backups list
        self.refresh_available_backup_list()
        # and bind it to the treeview
        available_backup_list_widget = self.xml.get_widget('available_backup_list')
        available_backup_list_widget.set_model(self.available_backup_list)
        available_backup_list_widget.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("system snapshots", renderer, text=0)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_reorderable(True)
        column.set_sort_column_id(0)
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
        num = file_list_widget.append_column( gtk.TreeViewColumn("", gtk.CellRendererToggle(), active=3) )
        
        column = gtk.TreeViewColumn()
        column.set_title('file name')
        file_list_widget.append_column(column)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'pixbuf', 4)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, expand=True)
        column.add_attribute(renderer, 'text', 0)        
        
        num = file_list_widget.append_column( gtk.TreeViewColumn("size", gtk.CellRendererText(), text=1) )
        num = file_list_widget.append_column( gtk.TreeViewColumn("last modified", gtk.CellRendererText(), text=2) )
        for num in range(4):
            col = file_list_widget.get_column(num)
            col.set_resizable(True)
            col.set_clickable(True)
            col.set_sort_indicator(True)
            col.set_reorderable(True)
            col.set_sort_column_id(num)
        # and add its handlers
        file_list_widget.connect('row-activated', self.select_subdir)
        file_list_widget.connect('button-press-event', self.file_list_button_press_event)

        # bind toolbar functions
        self.xml.get_widget('backup_button').connect('clicked', self.run_backup)
        self.xml.get_widget('restore_button').connect('clicked', self.run_restore)
        self.xml.get_widget('refresh_button').connect('clicked', self.refresh_all)
        self.xml.get_widget('pardir_button').connect('clicked', self.select_pardir)
        self.xml.get_widget('home_button').connect('clicked', self.go_home)
        # self.xml.get_widget('location_field').connect('current-folder-changed', self.select_dir)
        
        # bind menu functions
        self.xml.get_widget('menuitem_about').connect('activate', self.show_about_dialog)
        self.xml.get_widget('menuitem_prefs').connect('activate', lambda w: prefs.PrefsGUI(self) )
        self.xml.get_widget('menuitem_backup_history').connect('activate', lambda w: history.HistoryGUI(self) )
        self.xml.get_widget('menuitem_quit').connect('activate', gtk.main_quit)
        menuitem_show_output = self.xml.get_widget('menuitem_show_output')
        menuitem_show_output.connect('activate', self.show_hide_output )
        menuitem_show_output.set_active(client.get_bool("/apps/flyback/show_output"))
        self.show_hide_output(menuitem_show_output)
        menuitem_show_opengl = self.xml.get_widget('menuitem_show_opengl')
        menuitem_show_opengl.set_active(client.get_bool("/apps/flyback/show_opengl"))
        menuitem_show_opengl.connect('activate', self.show_hide_opengl )
        self.show_hide_opengl(menuitem_show_opengl)
        menuitem_show_hidden_files = self.xml.get_widget('menuitem_show_hidden_files')
        menuitem_show_hidden_files.set_active(client.get_bool("/apps/flyback/show_hidden_files"))
        menuitem_show_hidden_files.connect('activate', lambda x: client.set_bool('/apps/flyback/show_hidden_files',x.get_active())==self.refresh_file_list() )
        menuitem_sort_dirs_first = self.xml.get_widget('menuitem_sort_dirs_first')
        menuitem_sort_dirs_first.set_active(client.get_bool("/apps/flyback/sort_dirs_first"))
        menuitem_sort_dirs_first.connect('activate', lambda x: client.set_bool('/apps/flyback/sort_dirs_first',x.get_active())==self.refresh_file_list() )
        
        # set current folder
        self.xml.get_widget('location_field').set_text(self.cur_dir)
        
        main_window.show()
        
        # if no external storage defined, show prefs
        if not client.get_string("/apps/flyback/external_storage_location"):
            prefs.PrefsGUI(self)





def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "b", ["backup"])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)
    # process options
    for o, a in opts:
        if o in ("-b", "--backup"):
            backup().backup()
            sys.exit(0)

    init_gtk()
    MainGUI()
    gtk.main()


if __name__ == "__main__":
    main()
        
