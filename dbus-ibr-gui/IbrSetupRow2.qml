
MbItemCol {
    id: root
    description: qsTr("Discharge")
    property variant bmsService     // our service

    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    height: 2*mbStyle.itemHeight

    // realsoc, fakesoc, restartsoc
    // lowest-cell, cell-cutoff
    values: [
                MbItemRow {
                    description: qsTr("SOC:")
                    mbStyle: IbrSmallStyle {}
                    values: [                                                                                                                         
                        MbTextValue {
                            item: VBusItem { value: "real" }
                            mbStyle: IbrSmallStyle {}
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Info/RealSoc");
                            mbStyle: IbrSmallStyle {}
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "fake" }
                            mbStyle: IbrSmallStyle {}
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Soc");
                            mbStyle: IbrSmallStyle {}
                            item.decimals:1;
                            item.unit: "%"
                        },
                        MbTextValue { 
                            item: VBusItem { value: "turnon" }
                            mbStyle: IbrSmallStyle {}
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/Info/TurnOnSoc")
                            mbStyle: IbrSmallStyle {}
                            item.decimals:1;
                            item.unit: "%"
                        }
                    ]
                },
                MbItemRow {
                    description: qsTr("Cutoff:")
                    mbStyle: IbrSmallStyle {}
                    values: [
                        MbTextValue {
                            item: VBusItem { value: "mincell" }
                            mbStyle: IbrSmallStyle {}
                        },
                        MbTextBlock { 
                            item.bind: bmsService.path("/System/MinCellVoltage");
                            mbStyle: IbrSmallStyle {}
                            item.decimals:3; 
                            item.unit: "V"
                        },  
                        MbTextValue {
                            item: VBusItem { value: "cutoff" }
                            mbStyle: IbrSmallStyle {}
                        },  
                        MbTextBlock {  
                            item.bind: bmsService.path("/Info/CutOffVoltage");
                            mbStyle: IbrSmallStyle {}
                            item.decimals:3; 
                            item.unit: "V"
                        }
/*
                        MbTextBlock {  
                            VBusItem { id: inv_state; bind: rsinverterPath+"/State" }
                            item: VBusItem { value: stateAsString(inv_state.value) }
                            mbStyle: IbrSmallStyle {}
                        },  
                        MbTextBlock {
                            item.bind: rsinverterPath+"/Ac/Out/L1/P";
                            mbStyle: IbrSmallStyle {}
                        }   
*/
                    ]
                }
    ]                       
}


