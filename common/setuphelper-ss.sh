
standardPromptAndActions='no'
source "/data/SetupHelper/HelperResources/IncludeHelpers"

serviceDir="/opt/victronenergy/service-templates"
servicesDir="$scriptDir/service-templates"

servicesList=( $( cd "$servicesDir"; ls -d * 2> /dev/null ) )
firstservice=${servicesList[0]}

# intercept installAllServices() call
installAllServices () {

    echo "intercept installAllService()"

    echo "calling : orig installService $firstservice"
	installService $firstservice

    # Eneable serial starter service
    for usbdev in $(ls /dev/ttyUSB* 2>/dev/null); do
        bn=$(basename $usbdev)
        echo "bn: $bn"
        pids=$(ps |grep "supervise.*$bn"|grep -v grep)
        if [ -z "$pids" ]; then
            dynservicedir="/service/${firstservice}.${bn}"
            echo "process \"supervise $firstservice for $bn\" ($dynservicedir) not running, activating..."
            if [ -e "$dynservicedir" ]; then
                echo "$dynservicedir exists, skipping"
                ls -ld $dynservicedir
                continue
            fi
            read -p "install $firstservice for device $bn to $dynservciedir (y/n)? "
            if [ "$REPLY" == "y" ]; then
                echo "enable ... $serviceDir/${firstservice} to $dynservicedir"
                cp -R "$serviceDir/${firstservice}" "$dynservicedir" 
                sed -i "s/TTY/$bn/g" "$dynservicedir/run"
                echo "start $dynservicedir service..."
                svc -u "$dynservicedir"
            fi
        else
            echo "<supervise.*$bn> running, do not activate service.."
        fi
    done
}

if [ $scriptAction == 'INSTALL' ] && ! $installFailed ; then
    # avoid setup of /service/<service> in installService()
    echo "touching /service/$firstservice"
    touch /service/$firstservice
fi

# Handle prompt and install app to /opt/victronenergy
source "/data/ibr-venus-services/common/setuphelper.sh"

echo "End setup, calling endScript to install serial starter service ..."
endScript '' 'INSTALL_SERVICES' ''
