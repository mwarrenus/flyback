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

import dircache
import desktop
import gconf
from datetime import datetime, timedelta
from time import strptime
import threading
import help_data
import config_backend
import getopt

#try
import pygtk
pygtk.require("2.0")
import gobject, gtk
import gtk.glade
import gnome.ui
import gobject
#except:


    
BACKUP_DIR_DATE_FORMAT = "%Y%m%d_%H%M%S.backup"

client = config_backend.GConfConfig()

def get_external_storage_location_lock():
    external_storage_location = client.get_string("/apps/flyback/external_storage_location")
    if not external_storage_location:
        external_storage_location = '/external_storage_location'
    lockfile = external_storage_location +'/flyback/lockfile.txt'

    if not os.path.isdir( external_storage_location +'/flyback' ):
        return "The external storage location you've specified does not exist.  Please update your preferences."
    if os.path.isfile(lockfile):
        return "The external storage location you've specified is already in use.  Please quit any other open instances of FlyBack (or wait for their backups to complete) before starting a new backup."
    else:
        f = open(lockfile,'w')
        f.write('delete this if FlyBack has crashed/been killed and refuses to start a new backup.\n')
        f.close()
        return None

def release_external_storage_location_lock():
    external_storage_location = client.get_string("/apps/flyback/external_storage_location")
    if not external_storage_location:
        external_storage_location = '/external_storage_location'
    lockfile = external_storage_location +'/flyback/lockfile.txt'

    os.remove(lockfile)
    
def get_x_years_ago(d, x):
    year, month, day = d.year, d.month, d.day
    year -= x
    try:
        return d.replace(year=year, month=month)
    except ValueError:
        print 'poop'
        try:
            return d.replace(year=year, month=month, day=day-1 )
        except ValueError:
            print 'poop2'

def get_x_months_ago(d, x):
    year, month, day = d.year, d.month, d.day
    month -= x
    while month <= 0:
        year -= 1; month += 12
    try:
        return d.replace(year=year, month=month)
    except ValueError:
        print 'poop'
        try:
            return d.replace(year=year, month=month, day=day-1 )
        except ValueError:
            print 'poop2'
            try:
                return d.replace(year=year, month=month, day=day-2 )
            except ValueError:
                print 'poop3'
                try:
                    return d.replace(year=year, month=month, day=day-3 )
                except ValueError:
                    print 'poop4'

def get_x_days_ago(d, x):
    return d - timedelta(x)


class backup:
    
    xml = None
    main_gui = None
    parent_backup_dir = None
    included_dirs = []
    excluded_patterns = []

    def __init__(self, o=None):
        self.main_gui = o
        if o:
            self.xml = o.xml

    def get_available_backups(self):
        self.parent_backup_dir = client.get_string("/apps/flyback/external_storage_location")
        if not self.parent_backup_dir:
#            error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
#            error.set_markup('Please select an external storage location in the preferences window.')
#            error.show()
            return []
        self.parent_backup_dir += '/flyback'
        try:
            dirs = dircache.listdir(self.parent_backup_dir)
            dir_datetimes = []
            for dir in dirs:
                try:
                    dir_datetimes.append( datetime(*strptime(dir, BACKUP_DIR_DATE_FORMAT)[0:6]) )
                except:
                    pass # file not a backup
            dir_datetimes.sort(reverse=True)
            return dir_datetimes
        except:
            print 'no available backups found'
#            traceback.print_stack()
            return []
        
    def get_latest_backup_dir(self):
        available_backups = self.get_available_backups()
        if available_backups:
            return available_backups[0]
        else:
            return None
    
    def get_backup_command(self, latest_backup_dir, dir, new_backup):
        eds = []
        for x in self.excluded_patterns:
            eds.append( '--exclude="%s"' % x )
        return "nice -n19 rsync -av --one-file-system --delete "+ ' '.join(eds) +" '%s/' '%s/'" % (dir, new_backup + dir)
    
    def run_cmd_output_gui(self, cmd):
        if self.main_gui:
            text_view = self.xml.get_widget('backup_output_text')
            text_buffer = text_view.get_buffer()
        output = []

        if self.main_gui:
            gtk.gdk.threads_enter()
            text_buffer.insert( text_buffer.get_end_iter(), '$ '+ cmd +'\n' )
            gtk.gdk.threads_leave()
        stdin, stdout = os.popen4(cmd)
        for line in stdout:
            output.append(line)
            if self.main_gui:
                gtk.gdk.threads_enter()
                text_buffer.insert( text_buffer.get_end_iter(), line )
                text_view.scroll_to_mark(text_buffer.get_insert(), 0.499)
                gtk.gdk.threads_leave()
            else:
                print line
        if self.main_gui:
            gtk.gdk.threads_enter()
            text_buffer.insert( text_buffer.get_end_iter(), '\n' )
            gtk.gdk.threads_leave()
        stdin.close()
        stdout.close()
        return output
            
    def backup(self):
        if self.main_gui:
            backup_button = self.xml.get_widget('backup_button')

        msg = get_external_storage_location_lock()
        if msg:
            if self.main_gui:
                error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
                error.set_markup("<b>External Storage Location Error</b>\n\n"+msg)
                error.connect('response', lambda x,y: error.destroy())
                error.show()
            else:
                print msg
            return

        latest_backup_dir = self.get_latest_backup_dir()
        self.included_dirs = client.get_list("/apps/flyback/included_dirs")
        self.excluded_patterns = client.get_list("/apps/flyback/excluded_patterns")
        
        if not self.included_dirs:
            resp = 'No directories set to backup.  Please add something to the "included dirs" list in the preferences window.'
            if self.main_gui:
                error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, flags=gtk.DIALOG_MODAL )
                error.connect('response', lambda x,y: error.destroy())
                error.set_markup(resp)
                error.show()
            else:
                print resp

        new_backup = self.parent_backup_dir +'/'+ datetime.now().strftime(BACKUP_DIR_DATE_FORMAT)

        if self.main_gui:
            gtk.gdk.threads_enter()
            backup_button.set_label('Backup is running...')
            backup_button.set_sensitive(False)
            text_view = self.xml.get_widget('backup_output_text')
            text_buffer = text_view.get_buffer()
            text_buffer.delete( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
            gtk.gdk.threads_leave()

        if latest_backup_dir:
            last_backup = self.parent_backup_dir +'/'+ latest_backup_dir.strftime(BACKUP_DIR_DATE_FORMAT)
            self.run_cmd_output_gui("cp -al '%s' '%s'" % (last_backup, new_backup))
            self.run_cmd_output_gui("chmod u+w '%s'" % new_backup)
        
        for dir in self.included_dirs:
            self.run_cmd_output_gui("mkdir -p '%s'" % (new_backup + dir))
            cmd = self.get_backup_command(latest_backup_dir, dir, new_backup)
            self.run_cmd_output_gui(cmd)
        self.run_cmd_output_gui("chmod -w '%s'" % new_backup)
        
        self.check_for_too_old_backups()
        
        release_external_storage_location_lock()
        
        if self.main_gui:
            gtk.gdk.threads_enter()
            self.main_gui.refresh_available_backup_list()
            backup_button.set_label('Backup')
            backup_button.set_sensitive(True)
            gtk.gdk.threads_leave()

    def restore(self):
        restore_button = self.xml.get_widget('restore_button')

        src = self.parent_backup_dir +'/'+ self.main_gui.selected_backup.strftime(BACKUP_DIR_DATE_FORMAT) + self.main_gui.cur_dir
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
            file = src.rstrip('/') +'/'+ local_file
            print 'file', file
            if os.path.isdir(file):
                cmd = 'cp -vR "%s" "%s"' % (file, dest)
            else:
                cmd = 'cp -v "%s" "%s"' % (file, dest)
            file_pairs = self.run_cmd_output_gui(cmd)
#            for file_pair in file_pairs:
#                to_f = file_pair.split(' -> ')[1].strip("'`\n")
#                if os.path.isdir(to_f):
#                    cmd = 'chmod -R u+w "%s"' % to_f
#                else:
#                    cmd = 'chmod u+w "%s"' % to_f
#                self.run_cmd_output_gui(True,cmd)
            
        gtk.gdk.threads_enter()
        restore_button.set_label('Restore')
        restore_button.set_sensitive(True)
        gtk.gdk.threads_leave()
        
        
    def check_for_too_old_backups(self):
        if not client.get_bool('/apps/flyback/pref_delete_backups_after'):
            return
        
        pref_delete_backups_after_qty = client.get_int( '/apps/flyback/pref_delete_backups_after_qty')
        pref_delete_backups_after_unit = client.get_string( '/apps/flyback/pref_delete_backups_after_unit')
        
        delete_before_date = None
        if pref_delete_backups_after_unit=='years':
            delete_before_date = get_x_years_ago( datetime.now(), pref_delete_backups_after_qty )
        if pref_delete_backups_after_unit=='months':
            delete_before_date = get_x_months_ago( datetime.now(), pref_delete_backups_after_qty )
        if pref_delete_backups_after_unit=='days':
            delete_before_date = get_x_days_ago( datetime.now(), pref_delete_backups_after_qty )

        print 'delete_before_date', delete_before_date
        if delete_before_date:
            for x in self.get_available_backups():
                if x < delete_before_date:
                    backup_dir = self.parent_backup_dir +'/'+ x.strftime(BACKUP_DIR_DATE_FORMAT)
                    print 'backup_dir', backup_dir
                    self.run_cmd_output_gui("chmod u+w '%s'" % backup_dir)
                    self.run_cmd_output_gui("rm -Rf '%s'" % backup_dir)
                    
