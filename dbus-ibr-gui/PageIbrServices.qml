import com.victron.velib 1.0

MbPage {
	id: root

    property string bindPrefix   // our service name
    property variant service     // our service

    title: "IBR Services"

    // --- Inverter Discovery and Calculation (from IbrServiceRow3) ---
    property variant rsinverterPath: undefined
    property variant multiPath: undefined
    property string multiInPath: "/Ac/ActiveIn/L1/P"

    function discoverInverter() {
        for (var i = 0; i < DBusServices.count; i++)
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_INVERTER) {
                rsinverterPath = DBusServices.at(i).name
                return
            }
    }

    function discoverMulti() {
        for (var i = 0; i < DBusServices.count; i++) {
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_MULTI) {
                multiPath = DBusServices.at(i).name
                return
            }
            if ((DBusServices.at(i).type === DBusService.DBUS_SERVICE_MULTI_RS) && (DBusServices.at(i).name.search("socketcan")>0)) {
                multiPath = DBusServices.at(i).name
                multiInPath = "/Ac/In/1/L1/P"
                return
            }
        }
    }

    Component.onCompleted: {
        discoverInverter()
        discoverMulti()
    }

    VBusItem { id: rs_outpower; bind: rsinverterPath ? rsinverterPath + "/Ac/Out/L1/P" : "" }
    VBusItem { id: multi_state; bind: multiPath ? multiPath + "/State" : "" }
    VBusItem { id: multi_inpower; bind: multiPath ? multiPath + multiInPath : "" }
    VBusItem { id: multi_outpower; bind: multiPath ? multiPath + "/Ac/Out/L1/P" : "" }

    property bool rshack: (rsinverterPath !== undefined) && (multiPath !== undefined)
    property int multipower: multiPath ? (rshack ? ((multi_state.value == 0) ? 0 : -(multi_inpower.value - multi_outpower.value)) : -(multi_outpower.value + multi_inpower.value)) : 0
    property int totalInverterPower: (rs_outpower.value || 0) + multipower

    // --- Summary Items ---
    VBusItem { id: pvPower; bind: "com.victronenergy.system/Dc/Pv/Power"; unit: "W" }

    summary: [pvPower.text, totalInverterPower + "W"]

    model: VisibleItemModel {

        IbrServiceRow1 { }
        IbrServiceRow2 { bmsService: root.service; }
        IbrServiceRow3 { }
        IbrServiceDetails { bmsService: root.service; }

  } // visiblemodel

} // Page

