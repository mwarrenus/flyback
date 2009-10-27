#!/usr/bin/python
import os, sys
import settings


GUIS = set()


def register_gui(gui):
  GUIS.add( gui )
  
def unregister_gui(gui):
  GUIS.discard(gui)
  if not GUIS:
    import gtk
    gtk.main_quit()

def run_all_backups():
  pass
  
def launch_select_backup_gui():
  import select_backup_gui
  register_gui( select_backup_gui.GUI(register_gui, unregister_gui) )

if __name__=='__main__':
  import sys
  args = sys.argv[1:]
  
  if len(args):
    if args[0] in ('-b','--backup'):
      run_all_backups()
    else:
      print 'usage: python flyback.py [--backup]'
  else:
    import gobject, gnome, gtk
    gnome.init( settings.PROGRAM_NAME, settings.PROGRAM_VERSION )
    gobject.threads_init()
    gtk.gdk.threads_init()
    launch_select_backup_gui()
    gtk.main()

