REPOPATH=/home/pi/git-cfg/
DATEDASH=$(date +%m-%d-%Y-%N)

cp -r /home/pi/klipper_config/ $REPOPATH
git -C $REPOPATH checkout bf-a  # safety check
git -C $REPOPATH add $REPOPATH*
git -C $REPOPATH diff --cached --exit-code
if [ $? -ne 0 ]; then
	git -C $REPOPATH commit -m "bf-a automated $DATEDASH"
    git -C $REPOPATH push origin bf-a
    if [ $? -ne 0 ]; then
	    git -C $REPOPATH checkout -b bf-a-error-$DATEDASH
	    git -C $REPOPATH push -f origin bf-a-error-$DATEDASH
    fi
fi

