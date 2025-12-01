
MbItemCol {
    id: root
    description: qsTr("Discharge")
    property variant bmsService     // our service

    property IbrSmallStyle mbStyle: IbrSmallStyle {}

    height: 2*mbStyle.itemHeight

    // realsoc, fakesoc, restartsoc
    // lowest-cell, cell-cutoff
    values: [
                MbItemRow {
                    description: qsTr("SOC:")
                    mbStyle: root.mbStyle
                    values: [                                                                                                                         
                        MbTextValue {
                            item: VBusItem { value: "real" }
                            mbStyle: root.mbStyle
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Info/RealSoc");
                            mbStyle: root.mbStyle
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "fake" }
                            mbStyle: root.mbStyle
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Soc");
                            mbStyle: root.mbStyle
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "turnon" }
                            mbStyle: root.mbStyle
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Info/TurnOnSoc")
                            mbStyle: root.mbStyle
                            item.decimals:1;
                            item.unit: "%"
                        }
                    ]
                },
                MbItemRow {
                    description: qsTr("Cutoff:")
                    mbStyle: root.mbStyle
                            // property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
                    values: [
                        MbTextValue {
                            item: VBusItem { value: "mincell" }
                            mbStyle: root.mbStyle
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/System/MinCellVoltage");
                            mbStyle: root.mbStyle
                            item.decimals:3; 
                            item.unit: "V"
                        },  
                        MbTextValue {
                            item: VBusItem { value: "cutoff" }
                            mbStyle: root.mbStyle
                        },  
                        MbTextBlock {  
                            item.bind: bmsService.path("/Info/CutOffVoltage");
                            mbStyle: root.mbStyle
                            item.decimals:3; 
                            item.unit: "V"
                        }
/*
                        MbTextBlock {  
                            VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                            item: VBusItem { value: stateAsString(inv_state.value) }
                            mbStyle: root.mbStyle
                        },  
                        MbTextBlock {
                            item.bind: rsinverterPath+"/Ac/Out/L1/P";
                            mbStyle: root.mbStyle
                        }   
*/
                    ]
                }
    ]                       
}


