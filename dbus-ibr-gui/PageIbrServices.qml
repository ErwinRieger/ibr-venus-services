import QtQuick 
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
	id: root

    property string bindPrefix   // our service name
    property variant service     // our service

	title: "IBR Services" // service.description
	summary: "summary" // (!isParallelBms && state.item.value === 18) ? "Pending " + dcVoltage.text + " " + soc.item.format(0) : [soc.item.format(0), dcVoltage.text, dcCurrent.text]

    property VBusItem bmsItems: VBusItem { bind: Utils.path("com.victronenergy.system", "/AvailableBmsServices") } 
    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property VBusItem balanersRunning: VBusItem { bind: Utils.path(bindPrefix, "/Ess/Balancing") } 

    property variant sys: theSystem

	property MbStyle smallStyle: MbStyle { fontPixelSize: 14; itemHeight: 23; marginItemHorizontal: 2; marginItemVertical: 2; }

    function getnbms() {
        var n = bmsItems.value.length
        console.log(bmsItems)
        console.log(bmsItems.value)
        console.log("len " + n)
        return n
    }
    // property int nBms: bmsItems.valid ? bmsItems.value.length : 0
    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0

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

	Component.onCompleted: {
        discoverInverter()
        discoverMulti()
	}

    // Rs6000 inverter + multiplus in assisting mode. multiplus has his CT sensor
    // on the rs6000 output, so it adds the rs output power to itself!
    // To get the real output power of the multiplus, we have to subtract ac-out power
    // from ac-in (CT) power.
    property bool rshack: (rsinverterPath !== undefined) && (multiPath !== undefined)

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
    function mpptModeAsString(mode) {
	    switch (mode) {
	        case 0:
		        return "off"
	        case 1:
		        return "idle"
	        case 2:
		        return "run"
	    }
        return "--"
    }

    model: VisibleItemModel {

	    property VBusItem connected: VBusItem { id: connected; bind: service.path("/Connected") }

	    // property VBusItem nrOfPhasesItem: VBusItem { bind: service.path("/NrOfPhases") }
	    // property VBusItem phase: VBusItem { bind: service.path("/Ac/Phase") }

	    // property int nrOfPhases: nrOfPhasesItem.valid ? nrOfPhasesItem.value : 3
	    // property bool multiPhase: nrOfPhases > 1
	    // property bool hasL1: multiPhase && nrOfPhases >= 1 || phase.valid && phase.value === 0 || !phase.valid

	    MbItemCol {
		 description: qsTr("PV")
         height: 2*smallStyle.itemHeight
         VBusItem { id:mpptmode; bind: "com.victronenergy.ibrsystem/MppOperationMode" }
		 values: [
            MbItemRow {
		        description: qsTr("Erzeug:")
                mbStyle: smallStyle
			    values: [
                  MbTextBlock { 
                      item: VBusItem { value: mpptModeAsString(mpptmode.value) }
                      mbStyle: smallStyle
                  },
                  MbTextBlock { 
                    item: sys.pvCharger.power
                    mbStyle: smallStyle
                  },
                  MbTextBlock { 
                    item.bind: "com.victronenergy.ibrsystem/TotalPVYield";
                    mbStyle: smallStyle
                    item.decimals:3;
                    item.unit: "kWh"
                  }
                ]
            },
            MbItemRow {
		        description: qsTr("Ertrag:")
                mbStyle: smallStyle
			    values: MbTextBlock { 
                    item.bind: "com.victronenergy.ibrsystem/TotalPVEarnings";
                    mbStyle: smallStyle
                    item.decimals:3;
                    item.unit: "Eur"
                }
            }
		]
	    }

	    MbItemCol {
		 description: qsTr("Batt")
         height: (nBatt+1)*smallStyle.itemHeight
         VBusItem { id:cv; bind: service.path("/Info/MaxChargeVoltage") }
		 values: [
                  // Cv, Volt, Current, Min, Max, Soc
                  MbItemRow {
		            description: qsTr("BMS:")
                    mbStyle: smallStyle
			        values: [
                      MbTextBlock { 
                          item: VBusItem { value: "cv "+cv.format(2)+"V" }
                          mbStyle: smallStyle
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Voltage");
                    mbStyle: smallStyle
                        item.decimals:2;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Current");
                    mbStyle: smallStyle
                        item.decimals:1;
                        item.unit: "A"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MinCellVoltage");
                    mbStyle: smallStyle
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MaxCellVoltage");
                    mbStyle: smallStyle
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Soc");
                        mbStyle: smallStyle
                        item.decimals:1;
                        item.unit: "%"
                      }
                    ]
                  },
		          Repeater {
          			model: nBatt

                        // Current, Min, Max, Soc
          				// opacity: getScaledStrength(strength.value) >= (index + 1) ? 1 : 0.2
                        MbItemRow {
                            property string battDevice: battInfo.value[index*3]
                            property string battPath: "com.victronenergy.battery."+battDevice
	                        property string balancer:  ((balanersRunning.value !== undefined && balanersRunning.value.includes(battDevice)) ? "B on " : "B off")
	                        property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
		                    description: qsTr(battInfo.value[index*3+1])
                            mbStyle: smallStyle
			                values: [
                                MbTextBlock { 
                                    item: VBusItem { value: balancer }
                                    mbStyle: smallStyle
                                },
                                MbTextBlock { 
                                    item: VBusItem { value: vdiff.value*1000; decimals: 0; unit: "mV" }
                                    mbStyle: smallStyle
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Dc/0/Current";
                                    mbStyle: smallStyle
                                    item.decimals:1;
                                    item.unit: "A"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MinCellVoltage";
                                    mbStyle: smallStyle
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MaxCellVoltage";
                                    mbStyle: smallStyle
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Soc";
                                    mbStyle: smallStyle
                                    item.decimals:1;
                                    item.unit: "%"
                                }
                        ]
                    }
      			}
		 ]
        }

	    MbItemCol {

            id: ac_row
		    description: qsTr("AC")
            property int nRows: (((rsinverterPath === undefined) ? 0:1) + ((multiPath === undefined) ? 0:1))
            height: (nRows+1)*smallStyle.itemHeight

            VBusItem { id: inverter_outpower; bind: rsinverterPath+"/Ac/Out/L1/P" }
            VBusItem { id: multi_state; bind: multiPath+"/State" }
            VBusItem { id: multi_inpower; bind: multiPath+multiInPath }
            VBusItem { id: multi_outpower; bind: multiPath+"/Ac/Out/L1/P" }
            property int multipower: rshack ? ((multi_state.value == 0)? 0 : -(multi_inpower.value-multi_outpower.value)) : -(multi_outpower.value+multi_inpower.value)

		    values: [
                MbItemRow {
		            description: qsTr("Load:")
                    mbStyle: smallStyle
			        values: [
                        MbTextBlock { 
                            item: sys.acLoad.power
                            mbStyle: smallStyle
                        }
                    ]
                },
                MbItemRow {
                    visible: (rsinverterPath === undefined ? false:true)
		            description: qsTr("RS Inverter:")
                    mbStyle: smallStyle
	                        // property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
			        values: [
                        MbTextBlock { 
                            VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                            item: VBusItem { value: stateAsString(inv_state.value) }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rsinverterPath+"/Ac/Out/L1/P";
                            mbStyle: smallStyle
                        }
                    ]
                },
                MbItemRow {
                    visible: (multiPath === undefined ? false:true)
		            description: multiName
                    mbStyle: smallStyle
			        values: [
                        MbTextBlock { 
                            item: VBusItem { value: stateAsString(multi_state.value) }
                            mbStyle: smallStyle
                        },
                        // MbTextBlock { 
                            // item: VBusItem { value: "CT:"+ac_row.multictpower.toString()+"W" }
                            // mbStyle: smallStyle
                        // },
                        MbTextBlock { 
                            item: VBusItem { value: ac_row.multipower; unit:"W" }
                            mbStyle: smallStyle
                        }
                    ]
                }
		    ]
	    }

        // property VBusItem volumeUnit: VBusItem { bind: "com.victronenergy.settings/Settings/System/VolumeUnit" }
		MbSubMenu {
			id: detailsPage
			description: qsTr("Details")
			subpage: Component {
				PageIbrServicesSetup {
                    rootInfo: root
					title: detailsPage.description
                    mbStyle: smallStyle
					bindPrefix: "com.victronenergy.settings"
				}
			}
		}

  } // visiblemodel

} // Page
