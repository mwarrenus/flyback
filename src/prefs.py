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

import commands, os, pwd, sys
from common import *
import config_backend

client = config_backend.GConfConfig()


class PrefsGUI:
    
    xml = None
    main_gui = None
        
    pref_cron_minute_options = [
        ['on the hour', '0'],
        ['15 minutes after the hour', '15'],
        ['30 minutes after the hour', '30'],
        ['45 minutes after the hour', '45'],
        ['every half an hour', '0,30'],
        ['every 15 minutes', '0,15,30,45'],
    ]
    pref_cron_hour_options = [
        ['every hour', '*'],
        ['every other hour', '*/2'],
        ['every hour (8am-8pm)', '8-20'],
        ['every other hour (8am-8pm)', '8,10,12,14,16,18,20'],
        ['at noon and midnight', '0,12'],
        ['at 3am', '3'],
    ]
    pref_cron_day_week_options = [
        ['every day of the week', '*'],
        ['every weekday', '1,2,3,4,5'],
        ['on monday/wednesday/friday', '1,3,5'],
        ['on tuesday/thursday/saturday', '2,4,6'],
        ['only on sunday', '0'],
    ]
    pref_cron_day_month_options = [
        ['every day of the month', '*'],
        ['on the first of the month', '1'],
        ['on the 1st and the 15h', '1,15'],
        ['on the 1st, 10th and 20th', '1,10,20'],
        ['on the 1st, 8th, 16th and 24th', '1,8,16,24'],
    ]
    
    def should_we_uninstall_previous_users_crontab(self, x, y):
        print x,y
        #self.install_crontab(None, user=self.orig_backup_as_user)
            
    def save_prefs(self, o):
        client.set_string ("/apps/flyback/external_storage_location", self.external_storage_location )
        client.set_string ("/apps/flyback/external_storage_location_type", self.external_storage_location_type )
        client.set_list("/apps/flyback/included_dirs", self.included_dirs )
        client.set_bool( '/apps/flyback/prefs_only_one_file_system_checkbutton', self.xml.get_widget('prefs_only_one_file_system_checkbutton').get_active() )
        client.set_list("/apps/flyback/excluded_patterns", self.excluded_patterns )
        
        if self.xml.get_widget('pref_run_backup_automatically').get_active():
            crontab = self.save_crontab()
            client.set_string ("/apps/flyback/crontab", crontab )
            self.install_crontab(crontab)
        else:
            client.set_string ("/apps/flyback/crontab", '' )
            self.install_crontab(None)

        self.backup_as_user = self.user_list[ self.xml.get_widget('run_backup_as_user').get_active() ][0]
        if self.backup_as_user != self.orig_backup_as_user:
            error = gtk.MessageDialog( type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, flags=gtk.DIALOG_MODAL )
            error.set_markup("<b>The 'run as user' option has changed.</b>\n\nWould you like to uninstall the previous user's (%s) flyback crontab entry?" % self.orig_backup_as_user)
            error.connect('response', self.should_we_uninstall_previous_users_crontab )
            error.show()
                
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
        print 'saving prefs... [done]'
        
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
        
    def index_of_in_list_of_lists(self, value, list, column, not_found=-1):
        for i in range(0,len(list)):
            if value==list[i][column]:
                return i
        return not_found
        
    def load_crontab(self, s):
        self.xml.get_widget('pref_run_backup_automatically').set_active( bool(s) )
        self.xml.get_widget('pref_cron_minute').set_sensitive( bool(s) )
        self.xml.get_widget('pref_cron_hour').set_sensitive( bool(s) )
        self.xml.get_widget('pref_cron_day_week').set_sensitive( bool(s) )
        self.xml.get_widget('pref_cron_day_month').set_sensitive( bool(s) )
        min = '0'
        hour = '3'
        day_month = '*'
        month = '*'
        day_week = '*'
        
        try:
            sa = s.split(' ')
            min = sa[0]
            hour = sa[1]
            day_month = sa[2]
            #month = sa[3]
            day_week = sa[4]
        except:
            if s:
                print 'count not parse gconf /apps/flyback/crontab - using defaults'
        
        self.xml.get_widget('pref_cron_minute').set_active( self.index_of_in_list_of_lists( min, self.pref_cron_minute_options, 1, 0 ) )
        self.xml.get_widget('pref_cron_hour').set_active( self.index_of_in_list_of_lists( hour, self.pref_cron_hour_options, 1, 0 ) )
        self.xml.get_widget('pref_cron_day_month').set_active( self.index_of_in_list_of_lists( day_month, self.pref_cron_day_month_options, 1, 0 ) )
        self.xml.get_widget('pref_cron_day_week').set_active( self.index_of_in_list_of_lists( day_week, self.pref_cron_day_week_options, 1, 0 ) )

    def save_crontab(self):
        sa = []
        sa.append( self.pref_cron_minute_options[ self.xml.get_widget('pref_cron_minute').get_active() ][1] )
        sa.append( self.pref_cron_hour_options[ self.xml.get_widget('pref_cron_hour').get_active() ][1] )
        sa.append( self.pref_cron_day_month_options[ self.xml.get_widget('pref_cron_day_month').get_active() ][1] )
        sa.append( '*' )
        sa.append( self.pref_cron_day_week_options[ self.xml.get_widget('pref_cron_day_week').get_active() ][1] )
        return ' '.join(sa)
    
    def install_crontab(self, c, user=None):
        existing_crons = []
        if not user:
            user = self.backup_as_user
        print 'installing cron', c, 'for user', user
        
        stdin, stdout = os.popen4( '%s -u "%s" "crontab -l"' % (SU_COMMAND, user) )
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
        os.system( '%s -u "%s" "crontab /tmp/flyback_tmp_cron"' % (SU_COMMAND, user) )
    
    def check_crontab_entry(self, s):
        sa = s.replace(' ',',').replace(',,',',').split(',')
        if sa:
            return ','.join(sa)
        else:
            return '*'

    def set_model_from_list(self, cb, items, index=None):
        """Setup a ComboBox or ComboBoxEntry based on a list of strings."""           
        model = gtk.ListStore(str)
        for i in items:
            if index==None:
                model.append((i,))
            else:
                model.append((i[index],))
        cb.set_model(model)
        
    def change_external_storage_location_type(self, x):
        self.xml.get_widget('external_storage_location_drive').set_sensitive( x.name=='external_storage_location_use_drive' )
        self.xml.get_widget('external_storage_location_unmount').set_sensitive( x.name=='external_storage_location_use_drive' )
        self.xml.get_widget('external_storage_location_drive_refresh').set_sensitive( x.name=='external_storage_location_use_drive' )
        self.xml.get_widget('external_storage_location_dir').set_sensitive( x.name=='external_storage_location_use_dir' )
        self.xml.get_widget('external_storage_location_ssh').set_sensitive( x.name=='external_storage_location_use_ssh' )

    def update_external_storage_location_drives(self, o=None):
        external_storage_location = client.get_string("/apps/flyback/external_storage_location")
        self.drive_list.clear()
        icon_stock_harddisk = self.xml.get_widget('home_button').render_icon(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_DIALOG)
        icon_stock_network_disk = self.xml.get_widget('home_button').render_icon(gtk.STOCK_NETWORK, gtk.ICON_SIZE_DIALOG)
        index = 0
        select_index = -1
        for line in commands.getoutput('mount -v').split('\n'):
            loc = line[ line.index(' on ')+4 : line.index(' type ') ]
            type = line[ line.index(' type ')+6 : line.index(' ',line.index(' type ')+6) ]
            if loc=='/': continue
            if loc=='/boot': continue
            if type in ( 'fat', 'msdos', 'ntfs', 'vfat', 'usbfs', ): continue  # don't back up to file systems lacking hard-links
            if type in ('ext', 'ext2', 'ext3', 'fat', 'hfs', 'hpfs', 'jfs', 'minix', 'msdos', 'ntfs', 'ramfs', 'reiserfs', 'vfat', 'usbfs', 'xfs', ):
                self.drive_list.append( (loc, icon_stock_harddisk) )
                if external_storage_location==loc:
                    select_index = index
                index += 1
            if type in ('cifs', 'ncpfs', 'nfs', 'nfs4', 'smbfs', ):
                self.drive_list.append( (loc, icon_stock_network_disk) )
                if external_storage_location==loc:
                    select_index = index
                index += 1
        drive_list_widget = self.xml.get_widget('external_storage_location_drive')
        if select_index >= 0:
            drive_list_widget.select_path((select_index,))
            
    def set_ownership_of_dir_to_user( self, d ):
      os.popen( '%s "chown -R \'%s\' \'%s\'"' % (SU_COMMAND, USER, d) ).close()
        
    def check_write_perms_for_external_storage_location(self):
      external_storage_location = None
      if self.xml.get_widget('external_storage_location_use_dir').get_active():
        external_storage_location_type = 'dir'
        external_storage_location = self.xml.get_widget('external_storage_location_dir').get_current_folder()
      if self.xml.get_widget('external_storage_location_use_drive').get_active():
            external_storage_location_type = 'drive'
            sel = self.xml.get_widget('external_storage_location_drive').get_selected_items()
            if sel:
                external_storage_location = self.drive_list.get_value( self.drive_list.get_iter( sel[0] ), 0 )
        
      if external_storage_location:
        try:
          if not os.path.isdir(external_storage_location):
            os.mkdir(external_storage_location)
          if not os.path.isdir( os.path.join( external_storage_location, 'flyback' ) ):
            os.mkdir( os.path.join( external_storage_location, 'flyback' ) )
          test_fn = os.path.join( external_storage_location, 'flyback', '.flyback_test_write_access' )
          print test_fn
          f = open( test_fn, 'w' )
          f.close()
          os.remove(test_fn)
          self.external_storage_location = external_storage_location
          self.external_storage_location_type = external_storage_location_type
        except:
          error = gtk.MessageDialog( type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_YES_NO, flags=gtk.DIALOG_MODAL )
          error.set_markup("<b>External Storage Location Error</b>\n\n"+"You do not have write access to:\n%s\nWould you like to change its ownership to yourself?" % external_storage_location)
          if gtk.RESPONSE_YES==error.run():
            self.set_ownership_of_dir_to_user(external_storage_location)
            self.check_write_perms_for_external_storage_location()
          else:
            self.xml.get_widget('external_storage_location_drive').unselect_all()
          error.destroy()
          return
          

    def __init__(self, o):
        self.users = []
        self.included_dirs = []
        self.included_dirs_liststore = gtk.ListStore(gobject.TYPE_STRING)
        self.excluded_patterns = []
        self.excluded_patterns_liststore = gtk.ListStore(gobject.TYPE_STRING)
        self.pref_delete_backups_free_space_units = ['MB','GB']
        self.pref_delete_backups_after_units = ['days','months','years']
        self.drive_list = gtk.ListStore( str, gtk.gdk.Pixbuf )

        self.xml = o.xml
        self.main_gui = o
        
        # init external_storage_location
        external_storage_location = client.get_string("/apps/flyback/external_storage_location")
        external_storage_location_type = client.get_string("/apps/flyback/external_storage_location_type")
        print 'external_storage_location_type', external_storage_location_type
        if not external_storage_location:
            external_storage_location = '/external_storage_location'
        if not external_storage_location_type:
            external_storage_location_type = 'dir'
        self.xml.get_widget('external_storage_location_unmount').set_active( client.get_bool("/apps/flyback/external_storage_location_unmount") )
        if external_storage_location_type=='drive':
            self.xml.get_widget('external_storage_location_use_drive').set_active( True )
            self.xml.get_widget('external_storage_location_dir').set_sensitive( False )
            self.xml.get_widget('external_storage_location_drive').set_sensitive( True )
            self.xml.get_widget('external_storage_location_ssh').set_sensitive( False )
            self.xml.get_widget('external_storage_location_unmount').set_sensitive( True )
        if external_storage_location_type=='dir':
            self.xml.get_widget('external_storage_location_dir').set_current_folder( external_storage_location )
            self.xml.get_widget('external_storage_location_use_dir').set_active( True )
            self.xml.get_widget('external_storage_location_dir').set_sensitive( True )
            self.xml.get_widget('external_storage_location_drive').set_sensitive( False )
            self.xml.get_widget('external_storage_location_ssh').set_sensitive( False )
            self.xml.get_widget('external_storage_location_unmount').set_sensitive( False )
        if external_storage_location_type=='ssh':
            self.xml.get_widget('external_storage_location_use_ssh').set_active( True )
            self.xml.get_widget('external_storage_location_dir').set_sensitive( False )
            self.xml.get_widget('external_storage_location_drive').set_sensitive( False )
            self.xml.get_widget('external_storage_location_ssh').set_sensitive( True )
            self.xml.get_widget('external_storage_location_unmount').set_sensitive( False )
        self.xml.get_widget('external_storage_location_use_drive').connect('toggled', self.change_external_storage_location_type )
        self.xml.get_widget('external_storage_location_use_dir').connect('toggled', self.change_external_storage_location_type )
        self.xml.get_widget('external_storage_location_use_ssh').set_sensitive( False )
        self.xml.get_widget('external_storage_location_use_ssh').connect('toggled', self.change_external_storage_location_type )
        self.xml.get_widget('external_storage_location_drive_refresh').connect('clicked', self.update_external_storage_location_drives )
        drive_list_widget = self.xml.get_widget('external_storage_location_drive')
        drive_list_widget.set_model(self.drive_list)
        drive_list_widget.set_text_column(0)
        drive_list_widget.set_markup_column(0)
        drive_list_widget.set_pixbuf_column(1)
        drive_list_widget.set_orientation(gtk.ORIENTATION_VERTICAL)
        drive_list_widget.set_selection_mode(gtk.SELECTION_SINGLE)
        drive_list_widget.set_columns(10)
        drive_list_widget.connect('selection-changed', lambda x: self.check_write_perms_for_external_storage_location() )
        self.update_external_storage_location_drives()
        
        # init user
        self.user_list = pwd.getpwall()
        self.set_model_from_list( self.xml.get_widget('run_backup_as_user'), self.user_list, index=0 )
        self.orig_backup_as_user = client.get_string("/apps/flyback/backup_as_user")
        if not self.orig_backup_as_user:
            self.orig_backup_as_user = commands.getoutput("whoami")
        self.backup_as_user = self.orig_backup_as_user
        self.xml.get_widget('run_backup_as_user').set_active( self.index_of_in_list_of_lists( self.backup_as_user, self.user_list, 0, 0 ) )

        self.xml.get_widget('prefs_dialog').show()

        # init includes / excludes
        self.included_dirs = client.get_list("/apps/flyback/included_dirs")
        self.xml.get_widget('prefs_only_one_file_system_checkbutton').set_active( client.get_bool('/apps/flyback/prefs_only_one_file_system_checkbutton') )
        self.excluded_patterns = client.get_list("/apps/flyback/excluded_patterns", DEFAULT_EXCLUDES)
        
        # init backup crontab
        self.set_model_from_list( self.xml.get_widget('pref_cron_minute'), self.pref_cron_minute_options, index=0 )
        self.set_model_from_list( self.xml.get_widget('pref_cron_hour'), self.pref_cron_hour_options, index=0 )
        self.set_model_from_list( self.xml.get_widget('pref_cron_day_week'), self.pref_cron_day_week_options, index=0 )
        self.set_model_from_list( self.xml.get_widget('pref_cron_day_month'), self.pref_cron_day_month_options, index=0 )
        self.xml.get_widget('pref_run_backup_automatically').connect('toggled', lambda x: self.xml.get_widget('pref_cron_minute').set_sensitive(x.get_active()) == self.xml.get_widget('pref_cron_hour').set_sensitive(x.get_active()) == self.xml.get_widget('pref_cron_day_week').set_sensitive(x.get_active()) == self.xml.get_widget('pref_cron_day_month').set_sensitive(x.get_active())  )
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
        s = client.get_string('/apps/flyback/pref_delete_backups_free_space_unit', 'GB')
        self.set_model_from_list( widget_pref_delete_backups_free_space_unit, self.pref_delete_backups_free_space_units )
        widget_pref_delete_backups_free_space_unit.set_active_iter( widget_pref_delete_backups_free_space_unit.get_model().iter_nth_child( None, self.pref_delete_backups_free_space_units.index( s ) ) )
        s = client.get_string('/apps/flyback/pref_delete_backups_after_unit', 'years')
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

        

