#!/bin/sh

set -x
VERSION="`python src/settings.py`"
echo $VERSION
cd debs
mkdir flyback
cp ../src/* flyback
cd flyback
rm -Rf debs debian
find .hg | xargs rm -Rf
cd ..
mv flyback flyback-$VERSION
tar -czvvf flyback-$VERSION.tar.gz flyback-$VERSION
cd flyback-$VERSION
#dh_make -e public@kered.org -c GPL -f ../flyback-$VERSION.tar.gz 
cp -R ../../debian .
rm -Rf debian/.hg
echo "flyback ($VERSION-1) unstable; urgency=low" > debian/changelog
fakeroot debian/rules binary
cd ..
rm -Rf flyback
rm -Rf flyback-$VERSION
rm flyback-$VERSION.tar.gz
#svn add flyback_${VERSION}-1_all.deb

