#!/bin/sh
cd /home/ubuntu/samscloud_new/samscloud_api

git checkout master -f
git pull origin master
git reset --hard origin/master

. env/bin/activate
pip install -r requirements.txt
python manage.py migrate

sudo supervisorctl restart samscloud
sudo supervisorctl restart samscloudcelery
sudo supervisorctl restart samscloudcelerybeat
