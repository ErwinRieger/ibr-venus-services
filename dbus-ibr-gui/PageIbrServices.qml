import QtQuick 2
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
    property string rsinverterPath: undefined
    property string multiPath: undefined
    function discoverInverter() {
        for (var i = 0; i < DBusServices.count; i++)
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_INVERTER)
                rsinverterPath = DBusServices.at(i).name
    }
    function discoverMulti() {
        for (var i = 0; i < DBusServices.count; i++) 
            if (DBusServices.at(i).type === DBusService.DBUS_SERVICE_MULTI)
                multiPath = DBusServices.at(i).name
    }

	Component.onCompleted: {
        discoverInverter()
        discoverMulti()
	}

    property string stroff: "off"

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


    /* 
	property VBusItem dcVoltage: VBusItem { bind: service.path("/Dc/0/Voltage") }
	property VBusItem dcCurrent: VBusItem { bind: service.path("/Dc/0/Current") }
	property VBusItem midVoltage: VBusItem { bind: service.path("/Dc/0/MidVoltage") }
	property VBusItem productId: VBusItem { bind: service.path("/ProductId") }
	property VBusItem nrOfDistributors: VBusItem { bind: service.path("/NrOfDistributors") }
	property VBusItem nrOfBmses: VBusItem { bind: service.path("/NumberOfBmses") }

	property PageLynxDistributorList distributorListPage

	property bool isParallelBms: nrOfBmses.valid
	property bool isFiamm48TL: productId.value === 0xB012
	property int numberOfDistributors: nrOfDistributors.valid ? nrOfDistributors.value : 0
    */

    model: VisibleItemModel {

	    // property string acTotalPower: _acTotalPower.item.text
	    // property variant summary: connected.value === 1 ? acTotalPower : qsTr("Not connected")
	    property VBusItem connected: VBusItem { id: connected; bind: service.path("/Connected") }

	    property VBusItem nrOfPhasesItem: VBusItem { bind: service.path("/NrOfPhases") }
	    property VBusItem phase: VBusItem { bind: service.path("/Ac/Phase") }

	    property int nrOfPhases: nrOfPhasesItem.valid ? nrOfPhasesItem.value : 3
	    property bool multiPhase: nrOfPhases > 1
	    property bool hasL1: multiPhase && nrOfPhases >= 1 || phase.valid && phase.value === 0 || !phase.valid
	    property bool hasL2: multiPhase && nrOfPhases >= 2 || phase.valid && phase.value === 1
	    property bool hasL3: multiPhase && nrOfPhases >= 3 || phase.valid && phase.value === 2

	    function formatCgErrorCode(value)
	    {
		    if (value === undefined)
			    return "";
		    var text = qsTr("No error");
		    switch (value) {
		    case 1:
			    text = qsTr("Front selector locked");
			    break;
		    }
		    return text + " (" + value.toString() + ")";
	    }

	    function formatStatus(text, value)
	    {
		    return text + " (" + value.toString() + ")";
	    }

	    MbItemCol {
		 description: qsTr("PV")
         height: 2*smallStyle.itemHeight
         VBusItem { id:mpptmode; bind: "com.victronenergy.ibrsystem/MppOperationMode" }
		 values: [
            MbItemRow {
		        description: qsTr("Erzeug:")
                mbStyle: root.smallStyle
			    values: [
                  MbTextBlock { 
                      item: VBusItem { value: mpptModeAsString(mpptmode.value) }
                      mbStyle: root.smallStyle
                  },
                  MbTextBlock { 
                    item: sys.pvCharger.power
                    mbStyle: root.smallStyle
                  },
                  MbTextBlock { 
                    item.bind: "com.victronenergy.ibrsystem/TotalPVYield";
                    mbStyle: root.smallStyle
                    item.decimals:3;
                    item.unit: "kWh"
                  }
                ]
            },
            MbItemRow {
		        description: qsTr("Ertrag:")
                mbStyle: root.smallStyle
			    values: MbTextBlock { 
                    item.bind: "com.victronenergy.ibrsystem/TotalPVEarnings";
                    mbStyle: root.smallStyle
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
                    mbStyle: root.smallStyle
			        values: [
                      MbTextBlock { 
                          item: VBusItem { value: "cv "+cv.format(2)+"V" }
                          mbStyle: root.smallStyle
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Voltage");
                    mbStyle: root.smallStyle
                        item.decimals:2;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Current");
                    mbStyle: root.smallStyle
                        item.decimals:1;
                        item.unit: "A"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MinCellVoltage");
                    mbStyle: root.smallStyle
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MaxCellVoltage");
                    mbStyle: root.smallStyle
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Soc");
                    mbStyle: root.smallStyle
                        item.decimals:1;
                        item.unit: "%"
                      }
                    ]
                  },
		          Repeater {
          			model: nBatt

                        // Current, Min, Max, Soc
          				// color: root.color
          				// opacity: getScaledStrength(strength.value) >= (index + 1) ? 1 : 0.2
                        MbItemRow {
                            property string battDevice: battInfo.value[index*3]
                            property string battPath: "com.victronenergy.battery."+battDevice
	                        property string balancer:  ((balanersRunning.value !== undefined && balanersRunning.value.includes(battDevice)) ? "B on " : "B off")
	                        property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
		                    description: qsTr(battInfo.value[index*3+1])
                            mbStyle: root.smallStyle
			                values: [
                                MbTextBlock { 
                                    item: VBusItem { value: balancer }
                                    mbStyle: root.smallStyle
                                },
                                MbTextBlock { 
                                    item: VBusItem { value: vdiff.value*1000; decimals: 0; unit: "mV" }
                                    mbStyle: root.smallStyle
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Dc/0/Current";
                                    mbStyle: root.smallStyle
                                    item.decimals:1;
                                    item.unit: "A"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MinCellVoltage";
                                    mbStyle: root.smallStyle
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MaxCellVoltage";
                                    mbStyle: root.smallStyle
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Soc";
                                    mbStyle: root.smallStyle
                                    item.decimals:1;
                                    item.unit: "%"
                                }
                        ]
                    }
      			}
		 ]
        }

        // Rs6000 inverter + multiplus in assisting mode. multiplus has his CT sensor
        // on the rs6000 output, so it adds the rs output power to itself!
        // To get the real output power of the multiplus, we have to subtract ac-out power
        // from ac-in (CT) power.
	    MbItemCol {

            id: ac_row
		    description: qsTr("AC")
            property int nRows: ((rsinverterPath !== undefined ? 1:0) + (multiPath !== undefined ? 1:0))
            height: (nRows+1)*smallStyle.itemHeight

            VBusItem { id: multi_state; bind: multiPath+"/State" }
            VBusItem { id: multi_inpower; bind: multiPath+"/Ac/ActiveIn/L1/P" }
            VBusItem { id: multi_outpower; bind: multiPath+"/Ac/Out/L1/P" }
            VBusItem { id: inverter_outpower; bind: rsinverterPath+"/Ac/Out/L1/P" }
            property int multipower: (multi_state.value == 0)? 0 : (multi_outpower.value-multi_inpower.value)

		    values: [
                MbItemRow {
		            description: qsTr("Load:")
                    mbStyle: root.smallStyle
			        values: [
                        MbTextBlock { 
                            item: sys.acLoad.power
                            mbStyle: root.smallStyle
                        }
                    ]
                },
                MbItemRow {
                    show: (rsinverterPath !== undefined ? true:false)
		            description: qsTr("RS Inverter:")
                    mbStyle: root.smallStyle
	                        // property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
			        values: [
                        MbTextBlock { 
                            VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                            item: VBusItem { value: stateAsString(inv_state.value) }
                            mbStyle: root.smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rsinverterPath+"/Ac/Out/L1/P";
                            mbStyle: root.smallStyle
                        }
                    ]
                },
                MbItemRow {
                    show: (multiPath !== undefined ? true:false)
		            description: qsTr("RS Multi:")
                    mbStyle: root.smallStyle
			        values: [
                        MbTextBlock { 
                            item: VBusItem { value: stateAsString(multi_state.value) }
                            mbStyle: root.smallStyle
                        },
                        // MbTextBlock { 
                            // item: VBusItem { value: "CT:"+ac_row.multictpower.toString()+"W" }
                            // mbStyle: root.smallStyle
                        // },
                        MbTextBlock { 
                            item: VBusItem { value: ac_row.multipower; unit:"W" }
                            mbStyle: root.smallStyle
                        }
                    ]
                }
		    ]
	    }

        // Settings/IbrSystem/GridEnergyPrice
        // property VBusItem volumeUnit: VBusItem { bind: "com.victronenergy.settings/Settings/System/VolumeUnit" }
		MbSubMenu {
			id: settings
			description: qsTr("Settings")
			show: true // hasSettings.value === 1
			subpage: Component {
				PageIbrServicesSetup {
					title: settings.description
					bindPrefix: "com.victronenergy.settings"
				}
			}
		}

/*
	MbItemOptions {
		description: qsTr("Status")
		bind: service.path("/StatusCode")
		readonly: true
		show: valid
		possibleValues: [
			MbOption { description: formatStatus(qsTr("Startup"), 0); value: 0 },
			MbOption { description: formatStatus(qsTr("Startup"), 1); value: 1 },
			MbOption { description: formatStatus(qsTr("Startup"), 2); value: 2 },
			MbOption { description: formatStatus(qsTr("Startup"), 3); value: 3 },
			MbOption { description: formatStatus(qsTr("Startup"), 4); value: 4 },
			MbOption { description: formatStatus(qsTr("Startup"), 5); value: 5 },
			MbOption { description: formatStatus(qsTr("Startup"), 6); value: 6 },
			MbOption { description: qsTr("Running"); value: 7 },
			MbOption { description: qsTr("Standby"); value: 8 },
			MbOption { description: qsTr("Boot loading"); value: 9 },
			MbOption { description: qsTr("Error"); value: 10 },
			MbOption { description: qsTr("Running (MPPT)"); value: 11 },
			MbOption { description: qsTr("Running (Throttled)"); value: 12 }
		]
	}
	MbItemValue {
		description: qsTr("Error Code")
		item.bind: show ? service.path("/ErrorCode") : ""
		show: productIdItem.value === froniusInverterProductId
	}

	MbItemValue {
		description: qsTr("Error Code")
		item.text: formatCgErrorCode(cgErrorCode.value)
		show: productIdItem.value === carloGavazziEmProductId

		VBusItem {
			id: cgErrorCode
			bind: productIdItem.value === carloGavazziEmProductId ? service.path("/ErrorCode") : ""
		}
	}
*/

	MbItemRow {
		description: qsTr("AC Phase L1")
		values: [
			MbTextBlock { item.bind: service.path("/Ac/L1/Voltage"); width: 80; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L1/Current"); width: 100; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L1/Power"); width: 120; height: 25 }
		]
		show: false // hasL1
	}

	MbItemRow {
		description: qsTr("AC Phase L2")
		values: [
			MbTextBlock { item.bind: service.path("/Ac/L2/Voltage"); width: 80; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L2/Current"); width: 100; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L2/Power"); width: 120; height: 25 }
		]
		show: false // hasL2
	}

	MbItemRow {
		description: qsTr("AC Phase L3")
		values: [
			MbTextBlock { item.bind: service.path("/Ac/L3/Voltage"); width: 80; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L3/Current"); width: 100; height: 25 },
			MbTextBlock { item.bind: service.path("/Ac/L3/Power"); width: 120; height: 25 }
		]
		show: false // hasL3
	}


	MbItemValue {
		description: qsTr("Energy L1")
		item.bind: service.path("/Ac/L1/Energy/Forward")
		show: false // hasL1
	}

	MbItemValue {
		description: qsTr("Energy L2")
		item.bind: service.path("/Ac/L2/Energy/Forward")
		show: false // hasL2
	}

	MbItemValue {
		description: qsTr("Energy L3")
		item.bind: service.path("/Ac/L3/Energy/Forward")
		show: false // hasL3
	}

	MbItemValue {
		description: qsTr("Zero feed-in power limit")
		show: item.valid
		item.bind: service.path("/Ac/PowerLimit")
	}

	MbItemOptions {
		description: qsTr("Phase Sequence")
		bind: service.path("/PhaseSequence")
		readonly: true
		show: valid
		possibleValues: [
			MbOption { description: qsTr("L1-L2-L3"); value: 0 },
			MbOption { description: qsTr("L1-L3-L2"); value: 1 }
		]
	}
/*
	MbSubMenu {
		description: qsTr("Setup")
		show: subpage.show
		subpage: PageAcInSetup {
			title: qsTr("Setup")
			bindPrefix: bindPrefix
			productId: productIdItem.valid ? productIdItem.value : 0
		}
	}
	MbSubMenu {
		description: qsTr("Device")
		subpage: Component {
			PageDeviceInfo {
				title: qsTr("Device")
				bindPrefix: bindPrefix

				MbItemValue {
					description: qsTr("Data manager version")
					item.bind: service.path("/DataManagerVersion")
					show: item.valid
				}
			}
		}
	}
*/
    /*
	MbItemCol {
		 description: qsTr("PV")
         height: 2*smallStyle.itemHeight
		 values: [
	        Rectangle {
		        height: smallStyle.itemHeight
		        width: 100
		        color: "green"
	        },
	        Rectangle {
		        height: smallStyle.itemHeight
		        width: 100
		        color: "green"
	        }
        ]
    }
    */
  } // visiblemodel

} // Page
