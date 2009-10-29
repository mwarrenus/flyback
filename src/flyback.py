#!/usr/bin/python
import os, sys, traceback

import settings
import backup


GUIS = set()


def register_gui(gui):
  GUIS.add( gui )
  
def unregister_gui(gui):
  GUIS.discard(gui)
  if not GUIS:
    import gtk
    gtk.main_quit()

def run_all_backups():
  for t in backup.get_known_backups():
    uuid = t['uuid']
    host = t['host']
    path = t['path']
    if backup.test_backup_assertions(uuid, host, path):
      print '---=== starting backup:', uuid, path, '===---'
      try: backup.backup(uuid, host, path)
      except: traceback.print_exc()
    else:
      print '---=== skipped backup:', uuid, path, '===---'
  
def run_backup(uuid, path):
  host = backup.get_hostname()
  if backup.test_backup_assertions(uuid, host, path):
    print '---=== starting backup:', uuid, path, '===---'
    try: backup.backup(uuid, host, path)
    except: traceback.print_exc()
  else:
    print '---=== skipped backup:', uuid, path, '===---'
  
def launch_select_backup_gui():
  import select_backup_gui
  register_gui( select_backup_gui.GUI(register_gui, unregister_gui) )

if __name__=='__main__':
  import sys
  args = sys.argv[1:]
  
  if len(args):
    print
    print "------------------------------------------"
    print " FlyBack - Apple's Time Machine for Linux"
    print "------------------------------------------"
    print
    if args[0] in ('-b','--backup-all'):
      run_all_backups()
    elif len(args)==2:
      run_backup(args[0], args[1])
    else:
      print ' to launch the graphical interface:'
      print ' $ python flyback.py'
      print ' to backup all detected repositories:'
      print ' $ python flyback.py [-b|--backup-all]'
      print ' to backup a specific repository:'
      print ' $ python flyback.py <drive_uuid> <path>'
      print
  else:
    import gobject, gnome, gtk
    gnome.init( settings.PROGRAM_NAME, settings.PROGRAM_VERSION )
    gobject.threads_init()
    gtk.gdk.threads_init()
    launch_select_backup_gui()
    gtk.main()

