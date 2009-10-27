set -x
VERSION="0.5.1"
VERSION="${VERSION}_r`svnversion .`"
cd debs
mkdir flyback
cp ../src/* flyback
cd flyback
rm -Rf debs debian
find .svn | xargs rm -Rf
cd ..
mv flyback flyback-$VERSION
tar -czvvf flyback-$VERSION.tar.gz flyback-$VERSION
cd flyback-$VERSION
#dh_make -e public@kered.org -c GPL -f ../flyback-$VERSION.tar.gz 
cp -R ../../debian .
rm -Rf debian/.svn
echo "flyback ($VERSION-1) unstable; urgency=low" > debian/changelog
fakeroot debian/rules binary
cd ..
rm -Rf flyback
rm -Rf flyback-$VERSION
rm flyback-$VERSION.tar.gz
#svn add flyback_${VERSION}-1_all.deb

