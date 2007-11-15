rm -R flyback
mkdir flyback
cp src/*.py flyback/
cp src/*.glade flyback/
cp src/GPL.txt flyback/
tar -czvvf flyback.tar.gz flyback
