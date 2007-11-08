EXCLUDED_PATTERNS = '''
EXCLUDE PATTERNS

The exclude and include patterns specified to rsync allow for flexible selection of
which files to transfer and which files to skip.

rsync builds an ordered list of include/exclude options as specified on the 
command line. When a filename is encountered, rsync checks the name against each
 exclude/include pattern in turn. The first matching pattern is acted on. 
If it is an exclude pattern, then that file is skipped. 
If it is an include pattern then that filename is not skipped. 
If no matching include/exclude pattern is found then the filename is not skipped.

Note that when used with -r (which is implied by -a), every subcomponent of
every path is visited from top down, so include/exclude patterns get applied 
recursively to each subcomponent.

Note also that the --include and --exclude options take one pattern each.
To add multiple patterns use the --include-from and --exclude-from options
 or multiple --include and --exclude options.

The patterns can take several forms. The rules are:

# if the pattern starts with a / then it is matched against the start of the filename,
  otherwise it is matched against the end of the filename. 
  Thus "/foo" would match a file called "foo" at the base of the tree.
  On the other hand, "foo" would match any file called "foo" anywhere in the tree
  because the algorithm is applied recursively from top down; it behaves as if each
  path component gets a turn at being the end of the file name.

# if the pattern ends with a / then it will only match a directory, not a file,
  link or device.

# if the pattern contains a wildcard character from the set *?[ then expression
  matching is applied using the shell filename matching rules.
  Otherwise a simple string match is used.

# if the pattern includes a double asterisk "**" then all wildcards in the pattern
  will match slashes, otherwise they will stop at slashes.

# if the pattern contains a / (not counting a trailing /) then it is matched
  against the full filename, including any leading directory.
  If the pattern doesn't contain a / then it is matched only against the final
  component of the filename. Again, remember that the algorithm is applied recursively
  so "full filename" can actually be any portion of a path.

# if the pattern starts with "+ " (a plus followed by a space) then it is always
  considered an include pattern, even if specified as part of an exclude option.
  The "+ " part is discarded before matching.

# if the pattern starts with "- " (a minus followed by a space) then it is always
  considered an exclude pattern, even if specified as part of an include option.
  The "- " part is discarded before matching.

# if the pattern is a single exclamation mark ! then the current include/exclude list
  is reset, removing all previously defined patterns.

The +/- rules are most useful in exclude lists, allowing you to have a single
  exclude list that contains both include and exclude options.

If you end an exclude list with --exclude '*', note that since the algorithm is applied recursively that unless you explicitly include parent directories of files you want to include then the algorithm will stop at the parent directories and never see the files below them. To include all directories, use --include '*/' before the --exclude '*'.

Here are some exclude/include examples:

# --exclude "*.o"   would exclude all filenames matching *.o
# --exclude "/foo"  would exclude a file in the base directory called foo
# --exclude "foo/"  would exclude any directory called foo.
# --exclude "/foo/*/bar"  would exclude any file called bar two levels below a
                          base directory called foo.
# --exclude "/foo/**/bar" would exclude any file called bar two or more levels below
                          a base directory called foo.
# --include "*/" --include "*.c" --exclude "*"
                          would include all directories
                          and C source files
# --include "foo/" --include "foo/bar.c" --exclude "*"
                    would include only foo/bar.c (the foo/ directory must be
                    explicitly included or it would be excluded by the "*")
'''