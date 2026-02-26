
MbItemCol {

    id: ac_row

    description: qsTr("AC")

    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    // Check available services to find rs-inverter and multiplus
    property variant rsinverterPath: undefined
    property variant multiPath: undefined
    property string multiName: "Multiplus"
    property string multiInPath: "/Ac/ActiveIn/L1/P"

    function discoverInverter() {
        console.log("discover inverter")
        for (var i = 0; i < DBusServices.count; i++)
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_INVERTER) {
                rsinverterPath = DBusServices.at(i).name
                console.log("found inverter:"+ rsinverterPath)
                return
            }
        console.log("discover inverter, no result")
    }

    function discoverMulti() {
        console.log("discover multi")
        for (var i = 0; i < DBusServices.count; i++) {
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_MULTI) {
                multiPath = DBusServices.at(i).name
                console.log("found multi:"+ multiPath)
                return
            }
            if ((DBusServices.at(i).type === DBusService.DBUS_SERVICE_MULTI_RS) && (DBusServices.at(i).name.search("socketcan")>0)) {
                multiPath = DBusServices.at(i).name
                multiName = "Multi RS"
                multiInPath = "/Ac/In/1/L1/P"
                console.log("found multi:"+ multiPath)
                return
            }
        }
        console.log("discover multi, no result")
    }

    function stateAsString(state) {
        if (state === undefined)
            return "--"
	    var text = state.toString()
	    switch (state) {
	        case 0:
		        text = "off"
		        break;
	        case 2:
		        text = "fault"
		        break;
	        case 8:
		        text = "passth."
		        break;
	        case 9:
		        text = "invert."
		        break;
	        case 10:
		        text = "assist."
		        break;
	        case 252:
		        text = "extern."
		        break;
            default:
                console.log("PageIbrServices.qml:stateAsString(): unknown staate: "+state)
	    }
	    return text
    }

	Component.onCompleted: {
        discoverInverter()
        discoverMulti()
	}

    property int nRows: (((rsinverterPath === undefined) ? 0:1) + ((multiPath === undefined) ? 0:1))
    height: (nRows+1)*mbStyle.itemHeight
    
    // Rs6000 inverter + multiplus in assisting mode. multiplus has his CT sensor
    // on the rs6000 output, so it adds the rs output power to itself!
    // To get the real output power of the multiplus, we have to subtract ac-out power
    // from ac-in (CT) power.
    property bool rshack: (rsinverterPath !== undefined) && (multiPath !== undefined)
    
    VBusItem { id: inverter_outpower; bind: rsinverterPath+"/Ac/Out/L1/P" }
    VBusItem { id: multi_state; bind: multiPath+"/State" }
    VBusItem { id: multi_inpower; bind: multiPath+multiInPath }
    VBusItem { id: multi_outpower; bind: multiPath+"/Ac/Out/L1/P" }
    property int multipower: rshack ? ((multi_state.value == 0)? 0 : -(multi_inpower.value-multi_outpower.value)) : -(multi_outpower.value+multi_inpower.value)

    values: [
        MbItemRow {
            description: qsTr("Load:")
            mbStyle: IbrSmallStyle { }
            values: [
                MbTextBlock { 
                    item: theSystem.acLoad.power
                    mbStyle: IbrSmallStyle { }
                }
            ]
        },
        MbItemRow {
            visible: (rsinverterPath === undefined ? false:true)
            description: qsTr("RS Inverter:")
            mbStyle: IbrSmallStyle { }
            values: [
                MbTextBlock { 
                    VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                    item: VBusItem { value: stateAsString(inv_state.value) }
                    mbStyle: IbrSmallStyle { }
                },
                MbTextBlock { 
                    item.bind: rsinverterPath+"/Ac/Out/L1/P";
                    mbStyle: IbrSmallStyle { }
                }
            ]
        },
        MbItemRow {
            visible: (multiPath === undefined ? false:true)
            description: multiName
            mbStyle: IbrSmallStyle { }
            values: [
                MbTextBlock { 
                    item: VBusItem { value: stateAsString(multi_state.value) }
                    mbStyle: IbrSmallStyle { }
                },
                // MbTextBlock { 
                    // item: VBusItem { value: "CT:"+ac_row.multictpower.toString()+"W" }
                    // mbStyle: IbrSmallStyle { }
                // },
                MbTextBlock { 
                    item: VBusItem { value: ac_row.multipower; unit:"W" }
                    mbStyle: IbrSmallStyle { }
                }
            ]
        }
    ]
}

