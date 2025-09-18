
standardPromptAndActions='no'
source "/data/SetupHelper/HelperResources/IncludeHelpers"

serviceDir="/opt/victronenergy/service-templates"
servicesDir="$scriptDir/service-templates"

# intercept installService() call
originstallService=installService
myinstallService() {

    echo "intercept installService()"

    echo "calling : orig originstallService"
    $originstallService $*

    # Eneable serial starter service
    for usbdev in $(ls /dev/ttyUSB* 2>/dev/null); do
        bn=$(basename $usbdev)
        echo "bn: $bn"
        pids=$(ps |grep "supervise.*$bn"|grep -v grep)
        if [ -z "$pids" ]; then
            echo "process not running, activating..."
            dynservicedir="/service/${firstservice}.${bn}"
            if [ -e "$dynservicedir" ]; then
                echo "$dynservicedir exists, skipping"
                ls -ld $dynservicedir
                continue
            fi
            read -p "install for $bn to $dynservciedir (y/n)? "
            if [ "$REPLY" == "y" ]; then
                echo "enable ... $serviceDir/${firstservice} to $dynservicedir"
                cp -R "$serviceDir/${firstservice}" "$dynservicedir" 
                # ln -s "$serviceDir/${firstservice}" "$dynservicedir" 
            fi
        else
            echo "<supervise.*$bn> running, do not activate service.."
        fi
    done
}
installService=myInstallService

if [ $scriptAction == 'INSTALL' ] && ! $installFailed ; then
    # avoid setup of /service/<service> in installService()
    servicesList=( $( cd "$servicesDir"; ls -d * 2> /dev/null ) )
    firstservice=${servicesList[0]}
    echo "touching /service/$firstservice"
    touch /service/$firstservice
fi

# Handle prompt and install app to /opt/victronenergy
source "/data/ibr-venus-services/common/setuphelper.sh"

echo "End setup, calling endScript to install serial starter service ..."
endScript '' 'INSTALL_SERVICES' ''
