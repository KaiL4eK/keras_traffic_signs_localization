#!/bin/bash

for i in "$@"
do
case $i in
    -f|--full-sync)
		echo "Full sync"
		# Just to sync DB
		rsync -avzcLP -e "ssh -p 9992" VOCdevkit userquadro@uniq:~/yolo/
    ;;
    -c|--config-download)
		echo "Full sync"
		# Just to sync DB
		rsync -avzcLP -e "ssh -p 9992" userquadro@uniq:~/yolo/config.json .
    ;;
    *)
          # unknown option
    ;;
esac
done

rsync -avzcLP -e "ssh -p 9992" \
 \
*.json ext_repos *.py *.sh \
--exclude=.git --exclude=.gitignore --exclude=*.jpg --exclude=test_fld --exclude=__pycache__ \
userquadro@uniq:~/yolo/

