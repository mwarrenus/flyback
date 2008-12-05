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

import commands, datetime, math, os, pwd, sys, time
from common import *
import config_backend
import backup_backend


class HistoryGUI:
    
    xml = None
    main_gui = None
    
    treestore = gtk.TreeStore(str, str, str, 'gboolean') # type, start, time, error
    cmd_stdouts = {}
    cmd_stderrs = {}
    
    
    def refresh(self):
        self.treestore.clear()
        self.cmd_stdouts = {}
        self.cmd_stderrs = {}
        conn = backup_backend.get_or_create_db()
        c = conn.cursor()
        d = conn.cursor()
        xx = -1
        c.execute("select type, start_time, end_time, failure, id from operation order by id desc;")
        for x in c:
            xx += 1
            if x[0]=='backup': type = 'backup'
            if x[0]=='restore': type = 'restore'
            if x[0]=='delete_old_backups_to_free_space': type = 'cleanup'
            if x[0]=='delete_too_old_backups': type = 'cleanup'
            try:
                when = datetime.datetime(*time.strptime(x[1], backup_backend.BACKUP_DATE_FORMAT)[0:6])
                time_length = humanize_timedelta( datetime.datetime(*time.strptime(x[2], backup_backend.BACKUP_DATE_FORMAT)[0:6]) - when )
                when = when + backup_backend.get_tz_offset()
            except:
                print 'error:', sys.exc_info()
                when = ''
                time_length = ''
            iter = self.treestore.append(None, (type, when, time_length, not bool(x[3])) )
            
            d.execute("select cmd, stdout, stderr from command where operation_id=? order by id;", (x[4],) )
            yy = -1
            all_stdouts = []
            all_stderrs = []
            for y in d:
                yy += 1
                cmds = y[0].split()
                cmd = cmds[0]
                if cmd=='nice':
                    cmd = cmds[2]
                iter2 = self.treestore.append(iter, (cmd,'','','') )
                self.cmd_stdouts[(xx,yy)] = '$ '+ y[0] +'\n'+ y[1]
                self.cmd_stderrs[(xx,yy)] = '$ '+ y[0] +'\n'+ y[2]
                all_stdouts.append( self.cmd_stdouts[(xx,yy)] )
                all_stderrs.append( self.cmd_stderrs[(xx,yy)] )
            self.cmd_stdouts[(xx,)] = ''.join(all_stdouts)
            self.cmd_stderrs[(xx,)] = ''.join(all_stderrs)
            
        conn.close()
    
    def select_cmd(self, treeview):
        selection = treeview.get_selection()
        liststore, rows = selection.get_selected_rows()
        if rows:
            try:
                text_view = self.xml.get_widget('stdout')
                text_buffer = text_view.get_buffer()
#                text_buffer.delete( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
                text_buffer.set_text( self.cmd_stdouts[rows[0]] )
                text_view = self.xml.get_widget('stderr')
                text_buffer = text_view.get_buffer()
#                text_buffer.delete( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
                text_buffer.set_text( self.cmd_stderrs[rows[0]] )
            except:
                print 'error:', sys.exc_info()
                pass

    def __init__(self, o):
        self.xml = o.xml
        self.main_gui = o
        
        operation_list_widget = self.xml.get_widget('operation_list')
        operation_list_widget.set_model(self.treestore)
        operation_list_widget.set_headers_visible(True)
        #operation_list_widget.connect('button-press-event', self.include_dir_button_press_event)
        operation_list_widget.connect('cursor-changed', self.select_cmd)
        operation_list_widget.append_column( gtk.TreeViewColumn("action", gtk.CellRendererText(), text=0) )
        operation_list_widget.append_column( gtk.TreeViewColumn("when", gtk.CellRendererText(), text=1) )
        operation_list_widget.append_column( gtk.TreeViewColumn("time", gtk.CellRendererText(), text=2) )
        operation_list_widget.append_column( gtk.TreeViewColumn("success", gtk.CellRendererToggle(), active=3) )
        #operation_list_widget.append_column( gtk.TreeViewColumn("success", gtk.CellRendererText(), text=3) )
        self.refresh()

        # bind close button
        self.xml.get_widget('history_dialog_close').connect('clicked', lambda w: self.xml.get_widget('history_dialog').hide() )
        self.xml.get_widget('history_dialog_refresh').connect('clicked', lambda w: self.refresh() )

        self.xml.get_widget('history_dialog').show()

