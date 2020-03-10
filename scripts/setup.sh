for corpus in dem1921 ancor conll2012
do
   f=fasttext_${corpus}_filtered.zip
   wget http://boberle.com/files/misc/$f
   unzip $f
   rm $f
done
