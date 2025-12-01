
MbItemRow {
    property variant bmsService

    description: qsTr("BMS:")
    mbStyle: IbrSmallStyle { }

    values: [
        MbTextBlock { 
            VBusItem { id:cv; bind: bmsService.path("/Info/MaxChargeVoltage") }
            item.text: cv.valid ? "cv "+cv.format(2)+"V" : "--"
            mbStyle: IbrSmallStyle { }
        },
        MbTextBlock { 
            item.bind: bmsService.path("/Dc/0/Voltage");
            mbStyle: IbrSmallStyle { }
            item.decimals:2;
            item.unit: "V"
        },
        MbTextBlock { 
            item.bind: bmsService.path("/Dc/0/Current");
            mbStyle: IbrSmallStyle { }
            item.decimals:1;
            item.unit: "A"
        },
        MbTextBlock { 
            item.bind: bmsService.path("/System/MinCellVoltage");
            mbStyle: IbrSmallStyle { }
            item.decimals:3;
            item.unit: "V"
        },
        MbTextBlock { 
            item.bind: bmsService.path("/System/MaxCellVoltage");
            mbStyle: IbrSmallStyle { }
            item.decimals:3;
            item.unit: "V"
        },
        MbTextBlock { 
            item.bind: bmsService.path("/Soc");
            mbStyle: IbrSmallStyle { }
            item.decimals:1;
            item.unit: "%"
        }
    ]
}

