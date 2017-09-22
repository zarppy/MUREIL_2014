#!/bin/bash

copyfile="copyright.txt"

for i in `ls *.py`
do
    echo ${i}
    cat ${copyfile} ${i} > tmp
    mv tmp ${i}
done

for i in `ls */*.py`
do
    echo ${i}
    cat ${copyfile} ${i} > tmp
    mv tmp ${i}
done

for i in `ls */*/*.py`
do
    echo ${i}
    cat ${copyfile} ${i} > tmp
    mv tmp ${i}
done
