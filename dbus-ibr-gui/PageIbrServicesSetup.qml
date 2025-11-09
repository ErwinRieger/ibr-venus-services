import QtQuick 2
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
	id: root
	property string bindPrefix
	property int productId

    property MbPage rootInfo
    property MbStyle mbStyle // : MbStyle {}

	model: VisibleItemModel {
	    MbItemCol {
            description: qsTr("BattInfo")
            height: rootInfo.nBatt*root.mbStyle.itemHeight

            // VBusItem { id: inverter_outpower; bind: rsinverterPath+"/Ac/Out/L1/P" }
            // VBusItem { id: multi_state; bind: multiPath+"/State" }
            // VBusItem { id: multi_inpower; bind: multiPath+multiInPath }
            // VBusItem { id: multi_outpower; bind: multiPath+"/Ac/Out/L1/P" }
            // property int multipower: rshack ? ((multi_state.value == 0)? 0 : -(multi_inpower.value-multi_outpower.value)) : -(multi_outpower.value+multi_inpower.value)

		    values: [
		          Repeater {
          			model: nBatt
                        MbItemRow {
                            VBusItem { id: battDevice; value: rootInfo.battInfo.value[index*3] }
                            VBusItem { id: battName; value: rootInfo.battInfo.value[index*3+1] }
                            VBusItem { id: btId; value: rootInfo.battInfo.value[index*3+2] }
		                    description: battDevice.value
                            mbStyle: root.mbStyle
			                values: [
                                MbTextBlock { 
                                    item: battName
                                    mbStyle: root.mbStyle
                                },
                                MbTextBlock { 
                                    item: btId
                                    mbStyle: root.mbStyle
                                }
                            ]
                        }
                    }
            ]
		}

	    MbItemCol {
            description: qsTr("Discharge")
            // height: rootInfo.nBatt*root.mbStyle.itemHeight
            height: 2*root.mbStyle.itemHeight

            // VBusItem { id: inverter_outpower; bind: rsinverterPath+"/Ac/Out/L1/P" }
            // VBusItem { id: multi_state; bind: multiPath+"/State" }
            // VBusItem { id: multi_inpower; bind: multiPath+multiInPath }
            // VBusItem { id: multi_outpower; bind: multiPath+"/Ac/Out/L1/P" }
            // property int multipower: rshack ? ((multi_state.value == 0)? 0 : -(multi_inpower.value-multi_outpower.value)) : -(multi_outpower.value+multi_inpower.value)

            // realsoc, fakesoc, restartsoc
            // lowest-cell, cell-cutoff
		    values: [
                MbItemRow {
		            description: qsTr("SOC:")
                    mbStyle: smallStyle
			        values: [
                        MbTextValue { 
                            item: VBusItem { value: "real" }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rootInfo.service.path("/Info/RealSoc");
                            mbStyle: smallStyle
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "fake" }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rootInfo.service.path("/Soc");
                            mbStyle: smallStyle
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "turnon" }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rootInfo.service.path("/Info/TurnOnSoc")
                            mbStyle: smallStyle
                            item.decimals:1;
                            item.unit: "%"
                        }
                    ]
                },
                MbItemRow {
		            description: qsTr("Cutoff:")
                    mbStyle: smallStyle
	                        // property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
			        values: [
                        MbTextValue { 
                            item: VBusItem { value: "mincell" }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rootInfo.service.path("/System/MinCellVoltage");
                            mbStyle: smallStyle
                            item.decimals:3;
                            item.unit: "V"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "cutoff" }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rootInfo.service.path("/Info/CutOffVoltage");
                            mbStyle: smallStyle
                            item.decimals:3;
                            item.unit: "V"
                        }
/*
                        MbTextBlock { 
                            VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                            item: VBusItem { value: stateAsString(inv_state.value) }
                            mbStyle: smallStyle
                        },
                        MbTextBlock { 
                            item.bind: rsinverterPath+"/Ac/Out/L1/P";
                            mbStyle: smallStyle
                        }
*/
                    ]
                }
            ]
		}

		MbEditBox {
			description: qsTr("Energy Price")
            matchString: "0123456789.,"
            maximumLength: 3 
			item {
				bind: Utils.path(bindPrefix, "/Settings/IbrSystem/GridEnergyPrice")
				// text: item.valid ? em24SwitchText(item.value) : "--"
			}
		}
	}
}
