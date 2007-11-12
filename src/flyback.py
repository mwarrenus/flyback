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

import os, sys, traceback

RUN_FROM_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + '/'
VERSION = 'v0.3.3'
GPL = open( RUN_FROM_DIR + 'GPL.txt', 'r' ).read()

DEFAULT_EXCLUDES = [
    '/**/.thumbnails/',
    '/**/.mozilla/**/Cache/',
    '/**/.cache/tracker/',
    '/**/.Trash/',
    '/**/.emerald/themecache/',
    '/**/.fontconfig/*.cache*',
    '/**/.java/deployment/cache/',
    '/**/amarok/albumcovers/cache/',
    '/**/amarok/albumcovers/large/',
    '/**/.liferea*/mozilla/liferea/Cache/',
    '/**/.liferea*/cache/',
    '/**/.macromedia/Flash_Player/*SharedObjects/',
    '/**/.macromedia/Macromedia/Flash\ Player/*SharedObjects/',
    '/**/.metacity/sessions/',
    '/**/.nautilus/saved*',
    '/**/.mythtv/osdcache/',
    '/**/.mythtv/themecache/',
    '/**/var/cache/',
    '/**/workspace/.metadata/',
    '/**/.openoffice.org2/user/registry/cache/',
    '/**/.openoffice.org2/user/uno_packages/cache/',
    '/**/.grails/*/scriptCache/',
    '/**/.wine/drive_c/windows/temp/',
    '/dev/',
    '/proc/',
    '/sys/',
    '/tmp/',
]




import dircache
import desktop
import gconf
import pickle
from datetime import datetime
from time import strptime
import threading
import help_data
import getopt

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


client = gconf.client_get_default()
client.add_dir ("/apps/flyback", gconf.CLIENT_PRELOAD_NONE)

from backup_backend import *

gobject.threads_init()
gtk.gdk.threads_init()

class main_gui:
    
    xml = None
    selected_backup = None
    backup = None
    cur_dir = '/'
    available_backups = []
    available_backup_list = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
    file_list = gtk.ListStore(gobject.TYPE_STRING)
    backup_thread = None
    restore_thread = None
        
    def select_subdir(self, treeview, o1, o2):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()

        if self.selected_backup:
            focus_dir = self.backup.parent_backup_dir +'/'+ self.selected_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
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
            self.available_backup_list.append( (n,n) )
            
    def refresh_file_list(self):
        self.xml.get_widget('pardir_button').set_sensitive( self.cur_dir != '/' )
        self.file_list.clear()
        if self.selected_backup:
            focus_dir = self.backup.parent_backup_dir +'/'+ self.selected_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.cur_dir
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
        
    def show_hide_opengl(self, o):
        if o.get_active():
            self.xml.get_widget("window_opengl").show_all()
        else:
            self.xml.get_widget("window_opengl").hide()
        client.set_bool("/apps/flyback/show_opengl", o.get_active())
    
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
        menuitem_show_opengl = self.xml.get_widget('menuitem_show_opengl')
        menuitem_show_opengl.connect('activate', self.show_hide_opengl )
        menuitem_show_opengl.set_active(client.get_bool("/apps/flyback/show_opengl"))
        self.show_hide_opengl(menuitem_show_opengl)
        
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
    excluded_patterns = []
    excluded_patterns_liststore = gtk.ListStore(gobject.TYPE_STRING)
    pref_delete_backups_free_space_units = ['MB','GB']
    pref_delete_backups_after_units = ['days','months','years']
            
    def save_prefs(self, o):
        external_storage_location = self.xml.get_widget('external_storage_location').get_current_folder()
        client.set_string ("/apps/flyback/external_storage_location", external_storage_location )
        if not os.path.isdir(external_storage_location):
            os.mkdir(external_storage_location)
        if not os.path.isdir(external_storage_location + '/flyback'):
            os.mkdir(external_storage_location + '/flyback')
        client.set_string ("/apps/flyback/included_dirs", pickle.dumps(self.included_dirs) )
        client.set_string ("/apps/flyback/excluded_patterns", pickle.dumps(self.excluded_patterns) )
        if self.xml.get_widget('pref_run_backup_automatically').get_active():
            crontab = self.save_crontab()
            client.set_string ("/apps/flyback/crontab", crontab )
            self.install_crontab(crontab)
        else:
            client.set_string ("/apps/flyback/crontab", '' )
            self.install_crontab(None)
        
        # delete backups
        client.set_bool( '/apps/flyback/pref_delete_backups_free_space', self.xml.get_widget('pref_delete_backups_free_space').get_active() )
        client.set_int( '/apps/flyback/pref_delete_backups_free_space_qty', int( self.xml.get_widget('pref_delete_backups_free_space_qty').get_value() ) )
        widget_pref_delete_backups_free_space_unit = self.xml.get_widget('pref_delete_backups_free_space_unit')
        client.set_string( '/apps/flyback/pref_delete_backups_free_space_unit', widget_pref_delete_backups_free_space_unit.get_model().get_value( widget_pref_delete_backups_free_space_unit.get_active_iter(), 0 ) )
        client.set_bool( '/apps/flyback/pref_delete_backups_after', self.xml.get_widget('pref_delete_backups_after').get_active() )
        client.set_int( '/apps/flyback/pref_delete_backups_after_qty', int( self.xml.get_widget('pref_delete_backups_after_qty').get_value() ) )
        widget_pref_delete_backups_after_unit = self.xml.get_widget('pref_delete_backups_after_unit')
        client.set_string( '/apps/flyback/pref_delete_backups_after_unit', widget_pref_delete_backups_after_unit.get_model().get_value( widget_pref_delete_backups_after_unit.get_active_iter(), 0 ) )
            
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
            new_dir =  self.xml.get_widget('pattern_exclude').get_text()
            if new_dir not in self.excluded_patterns:
                self.excluded_patterns.append(new_dir)
                self.excluded_patterns.sort()
                self.refresh_excluded_patterns_list()

    def refresh_excluded_patterns_list(self):
        self.excluded_patterns_liststore.clear()
        for n in self.excluded_patterns:
            self.excluded_patterns_liststore.append( (n,) )
            
    def exclude_dir_key_press(self, treeview, o2):
        if o2.keyval==gtk.keysyms.Delete:
            print 'woot!!!'
            selection = treeview.get_selection()
            liststore, rows = selection.get_selected_rows()
            self.excluded_patterns.remove( liststore[rows[0]][0] )
            self.refresh_excluded_patterns_list()
            
    def delete_element(self, o, i, a, f):
        a.pop(i)
        f()
            
    def include_dir_button_press_event(self, treeview, event):
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
                delete = gtk.ImageMenuItem(stock_id=gtk.STOCK_DELETE)
                delete.connect( 'activate', self.delete_element, pthinfo[0][0], self.included_dirs, self.refresh_included_dirs_list )
                menu.append(delete)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.get_time())
            return True
   
    def exclude_dir_button_press_event(self, treeview, event):
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
                delete = gtk.ImageMenuItem(stock_id=gtk.STOCK_DELETE)
                delete.connect( 'activate', self.delete_element, pthinfo[0][0], self.excluded_patterns, self.refresh_excluded_patterns_list )
                menu.append(delete)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.get_time())
            return True
   
    def show_excluded_patterns_help(self, o):
        self.xml.get_widget('help_text').get_buffer().set_text(help_data.EXCLUDED_PATTERNS)
        self.xml.get_widget('help_window').show()
        
    def load_crontab(self, s):
        self.xml.get_widget('pref_run_backup_automatically').set_active( bool(s) )
        min = '0'
        hour = '3'
        day_month = '*'
        month = '*'
        day_week = '*'
        
        try:
            sa = s.split(' ')
            min = str(float(sa[0]))
            hour = sa[1]
            day_month = sa[2]
            month = sa[3]
            day_week = sa[4]
        except:
            print 'count not parse gconf /apps/flyback/crontab - using defaults'
        
        self.xml.get_widget('pref_crontab_min').set_value( float(min) )
        self.xml.get_widget('pref_crontab_hour').set_text( hour )
        self.xml.get_widget('pref_crontab_day_month').set_text( day_month )
        self.xml.get_widget('pref_crontab_month').set_text( month )
        self.xml.get_widget('pref_crontab_day_week').set_text( day_week )

    def save_crontab(self):
        sa = []
        sa.append( str(int(self.xml.get_widget('pref_crontab_min').get_value())) )
        sa.append( self.check_crontab_entry( self.xml.get_widget('pref_crontab_hour').get_text() ) )
        sa.append( self.check_crontab_entry( self.xml.get_widget('pref_crontab_day_month').get_text() ) )
        sa.append( self.check_crontab_entry( self.xml.get_widget('pref_crontab_month').get_text() ) )
        sa.append( self.check_crontab_entry( self.xml.get_widget('pref_crontab_day_week').get_text() ) )
        return ' '.join(sa)
    
    def install_crontab(self, c):
        existing_crons = []
        
        stdin, stdout = os.popen4('crontab -l')
        for line in stdout:
            if line.startswith('no crontab for'): continue
            if line.endswith('#flyback\n'): continue
            existing_crons.append(line)
        if c:
            existing_crons.append(c + ' python '+ os.getcwd() +'/flyback.py --backup #flyback\n')
        stdin.close()
        stdout.close()

        f = open('/tmp/flyback_tmp_cron', 'w')
        f.writelines( existing_crons )
        f.close()
        os.system('crontab /tmp/flyback_tmp_cron')
    
    def check_crontab_entry(self, s):
        sa = s.replace(' ',',').replace(',,',',').split(',')
        if sa:
            return ','.join(sa)
        else:
            return '*'

    def set_model_from_list (self, cb, items):
        """Setup a ComboBox or ComboBoxEntry based on a list of strings."""           
        model = gtk.ListStore(str)
        for i in items:
            model.append([i])
        cb.set_model(model)
#        if type(cb) == gtk.ComboBoxEntry:
#            cb.set_text_column(0)
#        elif type(cb) == gtk.ComboBox:
#            cell = gtk.CellRendererText()
#            cb.pack_start(cell, True)
#            cb.add_attribute(cell, 'text', 0)

    def __init__(self, o):
        self.xml = o.xml
        self.main_gui = o
        
        # init external_storage_location
        external_storage_location = client.get_string("/apps/flyback/external_storage_location")
        if not external_storage_location:
            external_storage_location = '/external_storage_location'
        self.xml.get_widget('external_storage_location').set_current_folder( external_storage_location )

        self.xml.get_widget('prefs_dialog').show()

        # init includes / excludes
        s = client.get_string("/apps/flyback/included_dirs")
        if s: self.included_dirs = pickle.loads(s)
        else: self.included_dirs = []
        s = client.get_string("/apps/flyback/excluded_patterns")
        if s: self.excluded_patterns = pickle.loads(s)
        else: self.excluded_patterns = DEFAULT_EXCLUDES
        
        # init backup crontab
        self.load_crontab( client.get_string("/apps/flyback/crontab") )
        
        # init backup auto-delete
        s = client.get_bool('/apps/flyback/pref_delete_backups_free_space')
        widget_pref_delete_backups_free_space = self.xml.get_widget('pref_delete_backups_free_space')
        widget_pref_delete_backups_free_space.set_active(s)
        widget_pref_delete_backups_free_space.connect('toggled', lambda x: self.xml.get_widget('pref_delete_backups_free_space_qty').set_sensitive(x.get_active())==self.xml.get_widget('pref_delete_backups_free_space_unit').set_sensitive(x.get_active())  )
        widget_pref_delete_backups_free_space_qty = self.xml.get_widget('pref_delete_backups_free_space_qty')
        widget_pref_delete_backups_free_space_qty.set_sensitive(s)
        widget_pref_delete_backups_free_space_qty.set_value( client.get_int('/apps/flyback/pref_delete_backups_free_space_qty') )
        widget_pref_delete_backups_free_space_unit = self.xml.get_widget('pref_delete_backups_free_space_unit')
        widget_pref_delete_backups_free_space_unit.set_sensitive(s)
        s = client.get_bool('/apps/flyback/pref_delete_backups_after')
        self.xml.get_widget('pref_delete_backups_after').set_active(s)
        self.xml.get_widget('pref_delete_backups_after').connect('toggled', lambda x: self.xml.get_widget('pref_delete_backups_after_qty').set_sensitive(x.get_active())==self.xml.get_widget('pref_delete_backups_after_unit').set_sensitive(x.get_active())  )
        self.xml.get_widget('pref_delete_backups_after_qty').set_sensitive(s)
        self.xml.get_widget('pref_delete_backups_after_qty').set_value( client.get_int('/apps/flyback/pref_delete_backups_after_qty') )
        widget_pref_delete_backups_after_unit = self.xml.get_widget('pref_delete_backups_after_unit')
        widget_pref_delete_backups_after_unit.set_sensitive(s)
        s = client.get_string('/apps/flyback/pref_delete_backups_free_space_unit')
        if not s: s = 'GB'
        self.set_model_from_list( widget_pref_delete_backups_free_space_unit, self.pref_delete_backups_free_space_units )
        widget_pref_delete_backups_free_space_unit.set_active_iter( widget_pref_delete_backups_free_space_unit.get_model().iter_nth_child( None, self.pref_delete_backups_free_space_units.index( s ) ) )
        s = client.get_string('/apps/flyback/pref_delete_backups_after_unit')
        if not s: s = 'years'
        self.set_model_from_list( widget_pref_delete_backups_after_unit, self.pref_delete_backups_after_units )
        widget_pref_delete_backups_after_unit.set_active_iter( widget_pref_delete_backups_after_unit.get_model().iter_nth_child( None, self.pref_delete_backups_after_units.index( s ) ) )
        
        # bind ok/cancel buttons
        self.xml.get_widget('prefs_dialog_ok').connect('clicked', self.save_prefs)
        self.xml.get_widget('prefs_dialog_cancel').connect('clicked', lambda w: self.xml.get_widget('prefs_dialog').hide() )

        # bind include/exclude dir buttons
        self.xml.get_widget('include_dir_add_button').connect('clicked', self.add_include_dir)
        self.xml.get_widget('dirs_include').connect('key-press-event', self.include_dir_key_press)
        self.xml.get_widget('button_add_pattern_exclude').connect('clicked', self.add_exclude_dir)
        self.xml.get_widget('patterns_exclude').connect('key-press-event', self.exclude_dir_key_press)
        self.xml.get_widget('help_pattern_exclude').connect('clicked', self.show_excluded_patterns_help)

        # build include/exclude lists
        dirs_includet_widget = self.xml.get_widget('dirs_include')
        dirs_includet_widget.set_model(self.included_dirs_liststore)
        dirs_includet_widget.set_headers_visible(True)
        dirs_includet_widget.connect('button-press-event', self.include_dir_button_press_event)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("included dirs", renderer, text=0)
        if not dirs_includet_widget.get_columns():
            dirs_includet_widget.append_column(column)
        self.refresh_included_dirs_list()
        dirs_excludet_widget = self.xml.get_widget('patterns_exclude')
        dirs_excludet_widget.set_model(self.excluded_patterns_liststore)
        dirs_excludet_widget.set_headers_visible(True)
        dirs_excludet_widget.connect('button-press-event', self.exclude_dir_button_press_event)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("exclude patterns", renderer, text=0)
        if not dirs_excludet_widget.get_columns():
            dirs_excludet_widget.append_column(column)
        self.refresh_excluded_patterns_list()

        
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

    main_gui()
    gtk.main()


if __name__ == "__main__":
    main()
        
