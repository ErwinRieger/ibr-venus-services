
standardPromptAndActions='no'

#### following line incorporates helper resources into this script
source "/data/SetupHelper/HelperResources/IncludeHelpers"

if [ -z "$scriptAction" ]; then
    standardActionPrompt
fi

# destination of program files in /opt/victronenergy (fileListVersionIndependent)
destdir="$(dirname $serviceDir)/$packageName"
echo "scriptAction: $scriptAction, destdir: $destdir"
if [ $scriptAction == 'INSTALL' ] && ! $installFailed ; then
    # copy program files to /opt/victronenergy
    mkdir -p $destdir
    touch $installedFilesList
    cat $pkgFileSets/fileListVersionIndependent | while read activeFile; do
        f="$destdir/$activeFile"
        echo "installing: $activeFile -> $f"
        cp -R $scriptDir/$activeFile $f
        if (( $( grep -c "$activeFile" "$installedFilesList" ) == 0 )); then
            echo "$activeFile" >> "$installedFilesList"
        fi
    done
elif [ $scriptAction == 'UNINSTALL' ] && ! $installFailed ; then
    # uninstall files from /opt/victronenergy
    cat $installedFilesList | while read activeFile; do
        f="$destdir/$activeFile"
        echo "removing: $f"
        if [ -d $f ]; then
            rm -rf "$f"
        else
            rm -f "$f"
        fi
        grep -v "$f" "$installedFilesList" | tee "$installedFilesList" > /dev/null
    done
else
    echo "ignoring script action: $scriptAction"
fi

